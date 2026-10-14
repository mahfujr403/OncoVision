"""Admin Knowledgebase Ingestion Endpoint (Temporary Migration & Onboarding Utility).

Provides a secure, administrative endpoint to execute or dry-run the curated
medical knowledgebase ingestion pipeline into PostgreSQL pgvector on Render's
free tier where shell access and background jobs are unavailable.

Key Safety Controls:
1. Feature Flag: `ADMIN_INGESTION_ENDPOINT_ENABLED` in `Settings` must be explicitly
   True; otherwise the router raises HTTP 404 (Not Found).
2. Administrative Authorization: Requires `require_admin` dependency; only verified
   users with `role == UserRole.ADMIN` can invoke it.
3. Dry-Run by Default: Does not generate embeddings or write to the database unless
   explicitly requested.
4. Explicit Live Opt-in: `dry_run=False` strictly requires `confirm_live_ingestion=True`
   in the request payload; otherwise HTTP 400 is raised.
5. In-process Concurrency Lock: Prevents overlapping ingestion runs on the active worker.
6. Error Sanitization: Never leaks database URLs, API keys, passwords, or full tracebacks.

Note on Concurrency and Exclusivity:
-----------------------------------
`_ingestion_lock` uses an in-process `asyncio.Lock` to guarantee mutual exclusion
for concurrent requests handled by this Uvicorn event loop. On Render's Free tier,
the service runs as a single container instance with 1 worker process, making this
lock effective for normal single-instance traffic.

Limitations:
- Multi-worker deployments (e.g. Uvicorn with `--workers > 1`): in-process locks are
  process-local and do not coordinate across multiple worker processes.
- Multi-instance / horizontally scaled deployments: in-process locks do not coordinate
  across separate containers or machines. True global exclusivity across distributed
  nodes would require a distributed lock (e.g., Redis `SET NX` or PostgreSQL advisory
  locks `pg_try_advisory_lock`).
- Secondary defense: The underlying `DocumentIngestionPipeline` relies on deterministic
  UUIDs and SHA-256 chunk hash checks, meaning overlapping runs would idempotently
  converge rather than corrupt data, but global exclusivity is bounded to this process.
"""

import asyncio
import logging
import re
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.app import TAG_ADMIN
from app.core.settings import get_settings
from app.database.session import get_db
from app.dependencies.auth import require_admin
from app.models.user import User
from app.rag.embeddings import EmbeddingService
from app.rag.ingestion import (
    DocumentIngestionPipeline,
    resolve_corpus_path,
)
from app.utils.response import success_response

logger = logging.getLogger(__name__)

# In-process lock to prevent overlapping ingestion runs on the current worker
_ingestion_lock = asyncio.Lock()


def verify_admin_ingestion_enabled() -> None:
    """Verify that the admin knowledgebase ingestion endpoint is enabled via settings."""
    settings = get_settings()
    if not getattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", False):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledgebase ingestion endpoint is not found or disabled.",
        )


def _sanitize_error(err_str: str, api_key: str | None = None) -> str:
    """Sanitize error messages to ensure zero secret disclosure in responses."""
    if not err_str:
        return "Unknown error"
    sanitized = str(err_str)
    if api_key and api_key in sanitized:
        sanitized = sanitized.replace(api_key, "[REDACTED_API_KEY]")
    # Redact Google API key formats (AIza followed by base64/URL-safe chars)
    sanitized = re.sub(r"AIza[0-9A-Za-z\-_]{12,}", "[REDACTED_API_KEY]", sanitized)
    # Redact generic key / api_key values
    sanitized = re.sub(
        r"(?:api[-_]?key|key)[=:\s]+['\"]?([a-zA-Z0-9_\-]+)",
        r"key=[REDACTED_KEY]",
        sanitized,
        flags=re.IGNORECASE,
    )
    # Redact database connection strings (postgresql://..., postgresql+asyncpg://...)
    sanitized = re.sub(
        r"(?:postgresql(?:\+[a-z0-9]+)?):\/\/[^\s]+",
        "[REDACTED_DATABASE_URL]",
        sanitized,
    )
    # Redact password parameters
    sanitized = re.sub(
        r"(?:password|passwd)[=:\s]+['\"]?([^\s'\"]+)",
        r"password=[REDACTED_PASSWORD]",
        sanitized,
        flags=re.IGNORECASE,
    )
    # Redact external URLs
    sanitized = re.sub(r"https?://\S+", "[REDACTED_URL]", sanitized)

    # Classify recognizable upstream conditions into safe descriptions
    lower = sanitized.lower()
    if "429" in lower or "quota" in lower or "resource_exhausted" in lower:
        return "Upstream quota exceeded or rate limited by Gemini API."
    if "403" in lower or "permission_denied" in lower:
        return "Upstream permission or authentication error with Gemini API."

    if len(sanitized) > 150:
        sanitized = sanitized[:150] + "..."
    return sanitized


class AdminIngestionRequest(BaseModel):
    """Request payload for triggering knowledgebase ingestion."""

    dry_run: bool = Field(
        default=True,
        description="Whether to perform a dry run (no embeddings generated or stored in database). Defaults to True.",
    )
    confirm_live_ingestion: bool = Field(
        default=False,
        description="Explicit confirmation required to execute live ingestion when dry_run=False.",
    )
    force: bool = Field(
        default=False,
        description="Force re-generation of embeddings even if content hashes match.",
    )
    target_document: str | None = Field(
        default=None,
        description="Optional filter to ingest a specific document only (matches filename or relative path substring).",
    )


class AdminIngestionStatsData(BaseModel):
    """Response payload data describing ingestion results."""

    dry_run: bool
    documents_discovered: int
    documents_ingested: int
    documents_skipped: int
    documents_excluded: int
    chunks_created: int
    chunks_updated: int
    chunks_removed: int
    embedding_api_calls: int
    duration_seconds: float
    errors: list[str]
    summary: str


router = APIRouter(
    prefix="/knowledge",
    tags=[TAG_ADMIN],
    dependencies=[Depends(verify_admin_ingestion_enabled)],
)


@router.post(
    "/ingest",
    status_code=status.HTTP_200_OK,
    summary="Admin Knowledgebase Ingestion",
    description=(
        "Administrative endpoint to trigger or dry-run the curated medical knowledgebase "
        "ingestion pipeline. Guarded by feature flag ADMIN_INGESTION_ENDPOINT_ENABLED and "
        "require_admin authorization."
    ),
    responses={
        200: {"description": "Ingestion job or dry-run completed successfully."},
        400: {"description": "Invalid parameters or missing live ingestion confirmation."},
        401: {"description": "Missing or invalid authentication credentials."},
        403: {"description": "The authenticated user is not an administrator."},
        404: {"description": "Endpoint disabled or feature flag inactive."},
        409: {"description": "An ingestion run is already in progress on this worker."},
        500: {"description": "Internal ingestion failure (sanitized)."},
    },
)
async def trigger_knowledge_ingestion(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: AdminIngestionRequest | None = None,
):
    """Execute or dry-run knowledgebase ingestion with safety constraints."""
    request_data = payload or AdminIngestionRequest()

    # Safety check: Live ingestion requires explicit opt-in confirmation
    if not request_data.dry_run and not request_data.confirm_live_ingestion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Live ingestion requires explicit opt-in: set confirm_live_ingestion=True alongside dry_run=False.",
        )

    # Concurrency check
    if _ingestion_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An ingestion run is already in progress on this worker. Please wait for it to complete.",
        )

    settings = get_settings()
    corpus_path = resolve_corpus_path(settings.KNOWLEDGE_BASE_PATH)
    start_time = time.time()

    async with _ingestion_lock:
        try:
            if request_data.dry_run:
                pipeline = DocumentIngestionPipeline()
                stats = await pipeline.ingest_corpus(
                    corpus_path=corpus_path,
                    session=None,
                    force=request_data.force,
                    dry_run=True,
                    target_document=request_data.target_document,
                )
            else:
                if not settings.GOOGLE_API_KEY:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="GOOGLE_API_KEY is not configured on the server. Live ingestion cannot proceed.",
                    )
                from app.llm.client import get_gemini_client

                llm_client = get_gemini_client(settings.GOOGLE_API_KEY, settings.LLM_MODEL)
                embedding_service = EmbeddingService(llm_client)
                pipeline = DocumentIngestionPipeline(embedding_service=embedding_service)
                stats = await pipeline.ingest_corpus(
                    corpus_path=corpus_path,
                    session=db,
                    force=request_data.force,
                    dry_run=False,
                    target_document=request_data.target_document,
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Knowledgebase ingestion failed: %s", exc, exc_info=True)
            sanitized_detail = _sanitize_error(str(exc), settings.GOOGLE_API_KEY)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Knowledgebase ingestion failed: {sanitized_detail}",
            )

        sanitized_errors = [
            _sanitize_error(err, settings.GOOGLE_API_KEY)
            for err in stats.errors
        ]
        duration = time.time() - start_time

        data = AdminIngestionStatsData(
            dry_run=request_data.dry_run,
            documents_discovered=stats.documents_discovered,
            documents_ingested=stats.documents_ingested,
            documents_skipped=stats.documents_skipped,
            documents_excluded=stats.documents_excluded,
            chunks_created=stats.chunks_created,
            chunks_updated=stats.chunks_updated,
            chunks_removed=stats.chunks_removed,
            embedding_api_calls=stats.embedding_api_calls,
            duration_seconds=round(duration, 3),
            errors=sanitized_errors,
            summary=stats.summary(),
        )

        message = (
            "Knowledgebase dry-run completed successfully."
            if request_data.dry_run
            else "Knowledgebase live ingestion completed successfully."
        )

        return success_response(
            data=data.model_dump(),
            message=message,
        )
