"""Admin Prediction/History Oversight endpoints (Phase 7.4/7.6, ADR-036).

Routers only receive requests and delegate to `AdminHistoryService`; no
business logic lives here, matching the convention already established
by `app.api.v1.history.router`. Prediction History remains immutable and
append-only: this router exposes GET endpoints only -- there is no
create/update/delete operation anywhere in this module.

Exposes:

    GET /api/v1/admin/history
    GET /api/v1/admin/history/{history_id}
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.v1.admin.examples import ADMIN_HISTORY_NOT_FOUND_EXAMPLE, FORBIDDEN_ERROR_EXAMPLE
from app.api.v1.predictions.examples import AUTHENTICATION_ERROR_EXAMPLE, INTERNAL_ERROR_EXAMPLE
from app.constants.app import TAG_ADMIN
from app.core.logging import get_logger
from app.dependencies.auth import require_admin
from app.dependencies.services import get_admin_history_service
from app.history.exceptions import PredictionHistoryNotFoundError
from app.history.filters import PredictionHistoryFilter
from app.history.pagination import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
    PredictionHistoryPageRequest,
)
from app.history.prediction_history import PredictionHistory
from app.models.user import User
from app.schemas.admin import (
    AdminHistoryDetailResponseSchema,
    AdminHistoryItemSchema,
    AdminHistoryListResponseSchema,
    AdminPaginationSchema,
    PredictionHistoryModelEntrySchema,
    PredictionHistoryStatus,
)
from app.schemas.response import APIResponse
from app.services.admin_history_service import AdminHistoryService
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/history", tags=[TAG_ADMIN])


def _build_admin_history_item(history: PredictionHistory, user_email: str) -> AdminHistoryItemSchema:
    """Project a `PredictionHistory` domain object onto the Admin API contract.

    Mirrors `app.api.v1.history.router._build_history_item()`, extended
    with `user_id` and `user_email` -- fields administrative oversight
    needs but self-service retrieval does not (ADR-036). `user_email` is
    resolved separately (`AdminHistoryService.get_user_email(s)`) since
    `PredictionHistory` itself only carries the owning `user_id`.
    """
    individual_predictions = [
        PredictionHistoryModelEntrySchema(
            model_name=entry.model_name,
            prediction=entry.prediction,
            confidence=entry.confidence,
            inference_time_ms=entry.inference_time_ms,
        )
        for entry in history.summary.individual_predictions
    ]

    return AdminHistoryItemSchema(
        history_id=history.history_id,
        request_id=history.request_id,
        user_id=history.user_id,
        user_email=user_email,
        status=history.status,
        created_at=history.created_at,
        image_filename=history.metadata.image_filename,
        predicted_class=history.summary.predicted_class,
        confidence=history.summary.confidence,
        agreement_ratio=history.summary.agreement_ratio,
        successful_models=list(history.summary.successful_models),
        failed_models=list(history.summary.failed_models),
        participating_models=history.summary.participating_models,
        individual_predictions=individual_predictions,
    )


def _build_admin_history_detail(
    history: PredictionHistory, user_email: str
) -> AdminHistoryDetailResponseSchema:
    """Project a `PredictionHistory` domain object onto the Admin detail contract."""
    base = _build_admin_history_item(history, user_email=user_email)

    return AdminHistoryDetailResponseSchema(
        **base.model_dump(),
        image_content_type=history.metadata.image_content_type,
        image_size_bytes=history.metadata.image_size_bytes,
        image_width=history.metadata.image_width,
        image_height=history.metadata.image_height,
        model_manifest_version=history.metadata.model_manifest_version,
        processing_time_ms=history.metadata.processing_time_ms,
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List prediction history across all users",
    description=(
        "Returns one page of prediction history records across every "
        "user, newest first. Optionally narrowed to a single user via "
        "`user_id`. Read-only: no inference, model loading, or history "
        "modification occurs here."
    ),
    response_model=APIResponse[AdminHistoryListResponseSchema],
    responses={
        200: {"description": "A page of prediction history was retrieved."},
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
async def list_history(
    _admin: Annotated[User, Depends(require_admin)],
    admin_history_service: Annotated[AdminHistoryService, Depends(get_admin_history_service)],
    page: Annotated[
        int, Query(ge=1, description="1-indexed page number to retrieve.")
    ] = DEFAULT_PAGE,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description="Maximum number of records to return for this page.",
        ),
    ] = DEFAULT_PAGE_SIZE,
    user_id: Annotated[
        str | None,
        Query(description="Restrict results to history records owned by this user."),
    ] = None,
    status_filter: Annotated[
        PredictionHistoryStatus | None,
        Query(alias="status", description="Restrict results to records with this outcome status."),
    ] = None,
    predicted_class: Annotated[
        str | None,
        Query(description="Restrict results to records with this final predicted class."),
    ] = None,
    start_date: Annotated[
        datetime | None,
        Query(description="Restrict results to records created on or after this timestamp."),
    ] = None,
    end_date: Annotated[
        datetime | None,
        Query(description="Restrict results to records created on or before this timestamp."),
    ] = None,
    min_confidence: Annotated[
        float | None,
        Query(ge=0.0, le=100.0, description="Restrict results to records with confidence >= this value."),
    ] = None,
    max_confidence: Annotated[
        float | None,
        Query(ge=0.0, le=100.0, description="Restrict results to records with confidence <= this value."),
    ] = None,
):
    """Return one page of prediction history across every user, newest first."""
    page_request = PredictionHistoryPageRequest(page=page, page_size=page_size)
    filters = PredictionHistoryFilter(
        status=status_filter,
        predicted_class=predicted_class,
        start_date=start_date,
        end_date=end_date,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
    )

    logger.info(
        "Admin history list requested: user_id=%s page=%d page_size=%d filtered=%s",
        user_id,
        page_request.page,
        page_request.page_size,
        not filters.is_empty,
    )

    page_result = await admin_history_service.list_history(
        page_request=page_request, filters=filters, user_id=user_id
    )

    email_by_user_id = await admin_history_service.get_user_emails(
        [record.user_id for record in page_result.items]
    )
    items = [
        _build_admin_history_item(
            record, user_email=email_by_user_id.get(record.user_id, "Unknown")
        )
        for record in page_result.items
    ]
    response_data = AdminHistoryListResponseSchema(
        items=items,
        count=len(items),
        pagination=AdminPaginationSchema(**page_result.metadata.model_dump()),
    )

    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Prediction history retrieved successfully.",
    )


@router.get(
    "/{history_id}",
    status_code=status.HTTP_200_OK,
    summary="Retrieve a single prediction history record",
    description=(
        "Returns the complete, immutable prediction information for a "
        "single history record, regardless of owner. Read-only: no "
        "inference, model loading, or history modification occurs here."
    ),
    response_model=APIResponse[AdminHistoryDetailResponseSchema],
    responses={
        200: {"description": "The requested prediction history record was retrieved."},
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        403: {
            "description": "The authenticated user is not an administrator.",
            "content": {"application/json": {"example": FORBIDDEN_ERROR_EXAMPLE}},
        },
        404: {
            "description": "No history record matches `history_id`.",
            "content": {"application/json": {"example": ADMIN_HISTORY_NOT_FOUND_EXAMPLE}},
        },
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def get_history_detail(
    _admin: Annotated[User, Depends(require_admin)],
    admin_history_service: Annotated[AdminHistoryService, Depends(get_admin_history_service)],
    history_id: Annotated[
        str, Path(description="Unique identifier of the history record to retrieve.")
    ],
):
    """Return the complete details of a single prediction history record, regardless of owner."""
    logger.info("Admin history detail requested: history_id=%s", history_id)

    history = await admin_history_service.get_history(history_id=history_id)

    if history is None:
        logger.warning("Admin history detail lookup failed: history_id=%s not_found=True", history_id)
        raise PredictionHistoryNotFoundError()

    user_email = await admin_history_service.get_user_email(history.user_id)
    response_data = _build_admin_history_detail(history, user_email=user_email)

    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Prediction history record retrieved successfully.",
    )
