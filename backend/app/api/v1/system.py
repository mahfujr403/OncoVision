"""System information endpoint.

Routers only receive requests and delegate to services; no business logic
lives here.
"""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.admin.examples import FORBIDDEN_ERROR_EXAMPLE
from app.api.v1.predictions.examples import AUTHENTICATION_ERROR_EXAMPLE, INTERNAL_ERROR_EXAMPLE
from app.constants.app import TAG_SYSTEM
from app.core.settings import get_settings
from app.dependencies.auth import require_admin
from app.dependencies.services import (
    get_ai_runtime_manager,
    get_model_metadata_service,
    get_system_service,
)
from app.llm.rate_limiter import RateLimiter
from app.ml.metadata.metadata_service import ModelMetadataService
from app.ml.runtime.runtime_manager import AIRuntimeManager
from app.models.user import User
from app.services.system_service import SystemService
from app.utils.response import success_response

router = APIRouter(tags=[TAG_SYSTEM])

_llm_test_rate_limiter = RateLimiter()


def _sanitize_gemini_error(err_str: str, api_key: str | None = None) -> str:
    """Sanitize error messages from upstream Gemini API calls.

    Guarantees that raw API keys, URLs, credentials, or internal stack traces
    are never disclosed in diagnostic responses.
    """
    if not err_str:
        return "Unknown error"

    sanitized = str(err_str)
    if api_key and api_key in sanitized:
        sanitized = sanitized.replace(api_key, "[REDACTED_API_KEY]")
    # Redact Google API key formats (AIza followed by base64/URL-safe chars)
    sanitized = re.sub(r"AIza[0-9A-Za-z\-_]{20,}", "[REDACTED_API_KEY]", sanitized)
    # Redact generic key / api_key values
    sanitized = re.sub(
        r"(?:api[-_]?key|key)[=:\s]+['\"]?([a-zA-Z0-9_\-]+)",
        r"key=[REDACTED_KEY]",
        sanitized,
        flags=re.IGNORECASE,
    )
    # Redact URLs and endpoints
    sanitized = re.sub(r"https?://\S+", "[REDACTED_URL]", sanitized)

    # Classify recognizable upstream conditions into safe descriptions
    lower_err = sanitized.lower()
    if "429" in lower_err or "resource_exhausted" in lower_err or "quota" in lower_err:
        return "Upstream quota exceeded or rate limited by Gemini API."
    if "403" in lower_err or "permission_denied" in lower_err or "api key" in lower_err:
        return "Upstream authentication or permission error with Gemini API."
    if "404" in lower_err or "not_found" in lower_err:
        return "Requested model not found upstream."

    # Bound message length to prevent leaking internal traces
    if len(sanitized) > 120:
        sanitized = sanitized[:120] + "..."
    return sanitized


@router.get(
    "/system",
    summary="System Information",
    description="Returns application metadata and runtime system information.",
)
async def get_system_info(
    system_service: SystemService = Depends(get_system_service),
):
    """Return application, runtime, and storage information."""
    system_info = system_service.get_system_info()
    return success_response(
        data=system_info.model_dump(),
        message="System information retrieved successfully.",
    )


@router.get(
    "/system/models",
    summary="Registered AI Models",
    description=(
        "Returns the registered model manifest, including enabled models, "
        "the manifest version, and local cache availability. Does not load "
        "any model into memory."
    ),
)
async def get_registered_models(
    metadata_service: ModelMetadataService = Depends(get_model_metadata_service),
):
    """Return the model registry summary: registered models, enabled models, and manifest version."""
    registry_summary = metadata_service.get_manifest_summary()
    return success_response(
        data=registry_summary.model_dump(),
        message="Registered models retrieved successfully.",
    )


@router.get(
    "/system/runtime",
    summary="AI Runtime Health",
    description=(
        "Returns AI Runtime Manager health: startup timing, loaded/failed/"
        "pending model counts, and current memory status. Never loads a "
        "model or performs inference."
    ),
)
async def get_runtime_health(
    runtime_manager: AIRuntimeManager = Depends(get_ai_runtime_manager),
):
    """Return the current AI Runtime Manager health snapshot."""
    runtime_status = await runtime_manager.health_service.runtime_status()
    return success_response(
        data=runtime_status,
        message="Runtime health retrieved successfully.",
    )


@router.get(
    "/system/models/status",
    summary="Model Runtime Status",
    description=(
        "Returns the current runtime lifecycle status of every registered "
        "model (registered, downloading, downloaded, loading, ready, "
        "failed, or disabled)."
    ),
)
async def get_model_runtime_status(
    runtime_manager: AIRuntimeManager = Depends(get_ai_runtime_manager),
):
    """Return per-model runtime lifecycle status."""
    model_statuses = await runtime_manager.get_all_model_status()
    return success_response(
        data={"models": model_statuses},
        message="Model runtime status retrieved successfully.",
    )


@router.get(
    "/system/test-llm",
    summary="Diagnose Google Gemini models",
    description=(
        "Administrative diagnostic endpoint to inspect available Google Gemini "
        "models and verify basic generation capabilities. Requires administrator privileges."
    ),
    responses={
        200: {"description": "LLM diagnostic complete."},
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        403: {
            "description": "The authenticated user is not an administrator.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
        429: {
            "description": "Rate limit exceeded for diagnostic LLM testing.",
        },
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def test_llm_models(
    admin: Annotated[User, Depends(require_admin)],
):
    """Diagnostic endpoint to inspect available Google Gemini models and verify generation."""
    settings = get_settings()

    # Rate limiting enforcement (in-memory sliding window per admin user)
    is_allowed = await _llm_test_rate_limiter.check_rate_limit(
        str(admin.id),
        max_requests=settings.SYSTEM_TEST_LLM_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.SYSTEM_TEST_LLM_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for diagnostic LLM testing. Please wait before retrying.",
        )

    if not settings.GOOGLE_API_KEY:
        return success_response(
            data={
                "configured_model": settings.LLM_MODEL,
                "available_models": [],
                "test_results": {},
                "warning": "GOOGLE_API_KEY is not configured.",
            },
            message="LLM diagnostic complete (API key not configured)",
        )

    from google import genai

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    diagnostic: dict = {
        "configured_model": settings.LLM_MODEL,
        "available_models": [],
        "test_results": {},
    }

    try:
        models = [m.name for m in client.models.list()]
        diagnostic["available_models"] = [
            m for m in models if "gemini" in m.lower() or "embed" in m.lower()
        ]
    except Exception as e:
        diagnostic["list_error"] = _sanitize_gemini_error(str(e), settings.GOOGLE_API_KEY)

    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-3.6-flash",
    ]
    for cand in candidates:
        try:
            resp = await client.aio.models.generate_content(
                model=cand,
                contents="ping",
            )
            diagnostic["test_results"][cand] = {
                "status": "success",
                "text": (resp.text or "")[:100],
            }
        except Exception as ex:
            diagnostic["test_results"][cand] = {
                "status": "error",
                "error": _sanitize_gemini_error(str(ex), settings.GOOGLE_API_KEY),
            }

    return success_response(data=diagnostic, message="LLM diagnostic complete")
