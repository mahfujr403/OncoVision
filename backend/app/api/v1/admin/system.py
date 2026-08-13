"""Admin System & Runtime Administration endpoint (Phase 7.5/7.6, ADR-036).

Routers only receive requests and delegate to `AdminSystemService`; no
business logic lives here. Reuses the existing `AIRuntimeManager` /
`SystemService` / database-connectivity check -- no second runtime
manager is introduced (ADR-036).

Exposes:

    GET /api/v1/admin/system
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.admin.examples import FORBIDDEN_ERROR_EXAMPLE
from app.api.v1.predictions.examples import AUTHENTICATION_ERROR_EXAMPLE, INTERNAL_ERROR_EXAMPLE
from app.constants.app import TAG_ADMIN
from app.core.logging import get_logger
from app.dependencies.auth import require_admin
from app.dependencies.services import get_admin_system_service
from app.models.user import User
from app.schemas.admin import AdminSystemStatusSchema
from app.schemas.response import APIResponse
from app.services.admin_system_service import AdminSystemService
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/system", tags=[TAG_ADMIN])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Administrative system status",
    description=(
        "Returns safe, aggregated operational metadata: application "
        "information, database connectivity, AI Runtime Manager health, "
        "and per-model runtime status. Never exposes secrets, "
        "credentials, environment variables, or other sensitive "
        "infrastructure information."
    ),
    response_model=APIResponse[AdminSystemStatusSchema],
    responses={
        200: {"description": "Administrative system status was retrieved."},
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
async def get_admin_system_status(
    _admin: Annotated[User, Depends(require_admin)],
    admin_system_service: Annotated[AdminSystemService, Depends(get_admin_system_service)],
):
    """Return a combined application/database/runtime/model status snapshot."""
    logger.info("Admin system status requested.")

    status_snapshot = await admin_system_service.get_system_status()

    return success_response(
        data=status_snapshot,
        message="Administrative system status retrieved successfully.",
    )
