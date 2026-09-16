"""System information endpoint.

Routers only receive requests and delegate to services; no business logic
lives here.
"""

from fastapi import APIRouter, Depends

from app.constants.app import TAG_SYSTEM
from app.dependencies.services import (
    get_ai_runtime_manager,
    get_model_metadata_service,
    get_system_service,
)
from app.ml.metadata.metadata_service import ModelMetadataService
from app.ml.runtime.runtime_manager import AIRuntimeManager
from app.services.system_service import SystemService
from app.utils.response import success_response

router = APIRouter(tags=[TAG_SYSTEM])


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


@router.get("/system/test-llm", summary="Diagnose Google Gemini models")
async def test_llm_models():
    """Diagnostic endpoint to inspect available Google Gemini models and verify generation."""
    from google import genai
    from app.core.settings import get_settings

    settings = get_settings()
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    
    diagnostic: dict = {
        "configured_model": settings.LLM_MODEL,
        "available_models": [],
        "test_results": {},
    }
    
    try:
        models = [m.name for m in client.models.list()]
        diagnostic["available_models"] = [m for m in models if "gemini" in m.lower() or "embed" in m.lower()]
    except Exception as e:
        diagnostic["list_error"] = str(e)
        
    candidates = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-3.6-flash"]
    for cand in candidates:
        try:
            resp = await client.aio.models.generate_content(
                model=cand,
                contents="ping",
            )
            diagnostic["test_results"][cand] = {"status": "success", "text": (resp.text or "")[:100]}
        except Exception as ex:
            diagnostic["test_results"][cand] = {"status": "error", "error": str(ex)}
            
    return success_response(data=diagnostic, message="LLM diagnostic complete")
