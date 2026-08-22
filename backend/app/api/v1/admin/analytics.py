"""Admin Prediction Analytics Oversight endpoints (Phase 7.7, ADR-036 extension).

Routers only receive requests and delegate to `AdminAnalyticsService`; no
business logic lives here, matching the convention already established
by `app.api.v1.admin.history`. This is a read-only operation: no AI
inference occurs, and no prediction data is ever modified.

Exposes:

    GET /api/v1/admin/analytics

Reuses `PredictionAnalyticsResponseSchema` (Phase 6.2, ADR-038) as-is --
the response shape is identical to the self-service `/reports/analytics`
endpoint; only the underlying history collection differs (every user's
records, or one user's via `?user_id=`, rather than only the
authenticated caller's own).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.admin.examples import FORBIDDEN_ERROR_EXAMPLE
from app.api.v1.predictions.examples import AUTHENTICATION_ERROR_EXAMPLE, INTERNAL_ERROR_EXAMPLE
from app.api.v1.reports import EXPORT_LIMIT_EXCEEDED_RESPONSE
from app.constants.app import TAG_ADMIN
from app.core.logging import get_logger
from app.dependencies.auth import require_admin
from app.dependencies.services import get_admin_analytics_service
from app.models.user import User
from app.schemas.reports import PredictionAnalyticsResponseSchema
from app.schemas.response import APIResponse
from app.services.admin_analytics_service import AdminAnalyticsService
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=[TAG_ADMIN])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Retrieve aggregated prediction analytics across every user, or one user",
    description=(
        "Returns the same aggregated analytics shape as "
        "`GET /api/v1/reports/analytics`, computed across every user's "
        "prediction history by default -- or, when `user_id` is supplied, "
        "narrowed to that one user (including an administrator's own "
        "history, since administrators are users like any other). "
        "Read-only: no AI inference occurs, and no prediction data is "
        "ever modified."
    ),
    response_model=APIResponse[PredictionAnalyticsResponseSchema],
    responses={
        200: {"description": "Aggregated prediction analytics were computed successfully."},
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        403: {
            "description": "The authenticated user is not an administrator.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
        413: EXPORT_LIMIT_EXCEEDED_RESPONSE,
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def get_admin_prediction_analytics(
    admin: Annotated[User, Depends(require_admin)],
    analytics_service: Annotated[AdminAnalyticsService, Depends(get_admin_analytics_service)],
    user_id: Annotated[
        str | None,
        Query(description="When supplied, narrows analytics to a single user's history."),
    ] = None,
) -> APIResponse[PredictionAnalyticsResponseSchema]:
    """Return aggregated prediction analytics across every user, or one user via `user_id`.

    Delegates entirely to `AdminAnalyticsService.compute_analytics()`. No
    aggregation, filtering, or business logic is performed in this
    router beyond passing `user_id` through and projecting the result
    onto its public schema, mirroring `get_prediction_analytics()` in
    `app.api.v1.reports`.
    """
    logger.info(
        "Admin prediction analytics requested: admin_id=%s scope=%s",
        admin.id,
        user_id or "all-users",
    )

    result = await analytics_service.compute_analytics(user_id=user_id)

    logger.info(
        "Admin prediction analytics completed: admin_id=%s scope=%s "
        "analytics_id=%s total_predictions=%d",
        admin.id,
        user_id or "all-users",
        result.analytics_id,
        result.total_predictions,
    )

    response_data = PredictionAnalyticsResponseSchema.from_domain(result)

    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Admin prediction analytics retrieved successfully.",
    )
