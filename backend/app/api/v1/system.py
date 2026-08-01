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
