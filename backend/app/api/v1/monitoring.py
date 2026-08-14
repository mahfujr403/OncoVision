"""Monitoring & Observability endpoint (Phase 8.1, ADR-036).

Routers only receive requests and delegate to `MonitoringService`; no
business logic lives here. Reuses the existing `AIRuntimeManager` /
`SystemService` / database-connectivity check -- no second runtime
manager is introduced (ADR-036).

Exposes:

    GET /api/v1/monitoring

Distinct from `GET /api/v1/admin/system` (`app.api.v1.admin.system`):
both consume the same underlying operational sources, but this endpoint
returns the strongly-typed `app.monitoring` domain projection intended
for operational monitoring/observability tooling, while
`/admin/system` remains the Administration domain's own dict-shaped
snapshot. Authorization is required here for the same reason it is
required there -- combined application/database/runtime/model status is
treated as administrative-grade operational information (ADR-036/ADR-047).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.admin.examples import FORBIDDEN_ERROR_EXAMPLE
from app.api.v1.predictions.examples import AUTHENTICATION_ERROR_EXAMPLE, INTERNAL_ERROR_EXAMPLE
from app.constants.app import TAG_MONITORING
from app.core.logging import get_logger
from app.dependencies.auth import require_admin
from app.dependencies.services import get_monitoring_service
from app.models.user import User
from app.schemas.monitoring import MonitoringStatusSchema
from app.schemas.response import APIResponse
from app.services.monitoring_service import MonitoringService
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=[TAG_MONITORING])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Operational monitoring status",
    description=(
        "Returns an aggregated operational monitoring snapshot: "
        "application health, database connectivity, AI Runtime Manager "
        "health, per-model availability, and aggregated HTTP/prediction "
        "request metrics for this process since startup (Phase 8.2). "
        "Read-only; never loads a model, performs inference, or modifies "
        "prediction history/reports. Never exposes secrets, credentials, "
        "environment variables, or other sensitive infrastructure "
        "information."
    ),
    response_model=APIResponse[MonitoringStatusSchema],
    responses={
        200: {"description": "Monitoring status was retrieved."},
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        403: {
            "description": "The authenticated user is not an administrator.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def get_monitoring_status(
    _admin: Annotated[User, Depends(require_admin)],
    monitoring_service: Annotated[MonitoringService, Depends(get_monitoring_service)],
):
    """Return a combined application/database/runtime monitoring snapshot."""
    logger.info("Monitoring status requested.")

    monitoring_result = await monitoring_service.get_monitoring_status()

    return success_response(
        data=monitoring_result.model_dump(),
        message="Monitoring status retrieved successfully.",
    )
