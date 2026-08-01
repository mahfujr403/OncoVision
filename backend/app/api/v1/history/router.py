"""Prediction History retrieval endpoints (Phase 5.3/5.4, ADR-034/ADR-035).

Routers only receive requests and delegate to services; no business logic
lives here, matching the convention already established by
`app.api.v1.predictions.router` (ADR-010).

This router exposes `GET /api/v1/predictions/history`, which returns one
page of the authenticated user's own stored prediction history, newest
first. Ownership is enforced end-to-end: the router passes only the
current user's own `user_id` through to
`PredictionHistoryService.list_history_page()`, which in turn is enforced
again at the repository's database query (ADR-034) -- a user can never
receive another user's history records.

Phase 5.4 (ADR-035) extends the Phase 5.3 endpoint with client-supplied
pagination (`page`, `page_size`) and optional filtering (`status`,
`predicted_class`, `start_date`, `end_date`, `min_confidence`,
`max_confidence`) query parameters. Every parameter is optional and
independently validated by FastAPI's `Query(...)` declarations (defense
in depth, mirroring how `PredictionRequestSchema` already duplicates
constraints between its Pydantic fields and its `as_form()` `Form(...)`
parameters) before being handed to the already-validated
`PredictionHistoryPageRequest` / `PredictionHistoryFilter` domain objects.
Constructing either of those with an internally inconsistent value (e.g.
`start_date` later than `end_date`, or `page_size` outside its allowed
range) raises a Pydantic `ValidationError`, which the existing global
exception handler (`app.core.exceptions.validation_exception_handler`)
already turns into a standard `422` response -- no try/except is needed
in this router.

The endpoint no longer relies on the internal, non-configurable
`Settings.PREDICTION_HISTORY_LIST_LIMIT` bound introduced in Phase 5.3:
client-supplied `page_size` is now itself bounded by
`PredictionHistoryPageRequest`'s own `le=100` constraint. The setting
remains defined in `app.core.settings` for backward compatibility and
potential reuse elsewhere.

A future History Detail API extends this router further without
requiring any change to the already-implemented
`PredictionHistoryService.list_history_page()` /
`PredictionHistoryRepository.list_by_user()` / `.count_by_user()`.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.history.examples import FILTER_VALIDATION_ERROR_EXAMPLE
from app.api.v1.history.responses import (
    PredictionHistoryItemSchema,
    PredictionHistoryListResponseSchema,
    PredictionHistoryModelEntrySchema,
    PredictionHistoryPaginationSchema,
    PredictionHistoryStatus,
)
from app.api.v1.predictions.examples import AUTHENTICATION_ERROR_EXAMPLE, INTERNAL_ERROR_EXAMPLE
from app.constants.app import TAG_PREDICTION_HISTORY
from app.core.logging import get_logger
from app.dependencies.auth import get_current_active_user
from app.dependencies.services import get_prediction_history_service
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
from app.schemas.response import APIResponse
from app.services.prediction_history_service import PredictionHistoryService
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/predictions/history", tags=[TAG_PREDICTION_HISTORY])


def _build_history_item(history: PredictionHistory) -> PredictionHistoryItemSchema:
    """Project an internal `PredictionHistory` domain object onto the public contract.

    `PredictionHistory` (`app.history.prediction_history`, ADR-032) is
    never returned to API clients directly; this is the router-owned
    translation into `PredictionHistoryItemSchema`. Every field is copied
    directly -- no calculation is performed here.
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

    return PredictionHistoryItemSchema(
        history_id=history.history_id,
        request_id=history.request_id,
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


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Retrieve a page of the authenticated user's prediction history",
    description=(
        "Returns one page of prediction history records owned by the "
        "authenticated user, newest first (ADR-034/ADR-035). Retrieval is "
        "completely independent from the Prediction Engine, AI Runtime "
        "Manager, and Adaptive Ensemble Engine -- no inference, model "
        "loading, or prediction recalculation occurs here. Ownership is "
        "enforced at the database query itself, so a user can never "
        "receive another user's history.\n\n"
        "Pagination is controlled by `page` (1-indexed, default "
        f"{DEFAULT_PAGE}) and `page_size` (default {DEFAULT_PAGE_SIZE}, "
        f"between {MIN_PAGE_SIZE} and {MAX_PAGE_SIZE}). Every response "
        "now carries a `pagination` block describing the full, optionally "
        "filtered result set.\n\n"
        "Filtering is entirely optional: `status`, `predicted_class`, "
        "`start_date`, `end_date`, `min_confidence`, and `max_confidence` "
        "may each be supplied independently and are combined with a "
        "logical AND. Supplying an internally inconsistent range (e.g. "
        "`start_date` later than `end_date`, or `min_confidence` greater "
        "than `max_confidence`) is rejected with `422`."
    ),
    response_model=APIResponse[PredictionHistoryListResponseSchema],
    responses={
        200: {"description": "A page of the authenticated user's prediction history was retrieved."},
        401: {
            "description": "Missing or invalid authentication credentials.",
            "content": {"application/json": {"example": AUTHENTICATION_ERROR_EXAMPLE}},
        },
        422: {
            "description": (
                "One or more query parameters failed validation -- either "
                "an out-of-range `page`/`page_size`, or an internally "
                "inconsistent filter range (`start_date` later than "
                "`end_date`, or `min_confidence` greater than "
                "`max_confidence`)."
            ),
            "content": {"application/json": {"example": FILTER_VALIDATION_ERROR_EXAMPLE}},
        },
        500: {
            "description": "An unexpected internal server error occurred.",
            "content": {"application/json": {"example": INTERNAL_ERROR_EXAMPLE}},
        },
    },
)
async def list_prediction_history(
    current_user: Annotated[User, Depends(get_current_active_user)],
    history_service: Annotated[PredictionHistoryService, Depends(get_prediction_history_service)],
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
    status_filter: Annotated[
        PredictionHistoryStatus | None,
        Query(
            alias="status",
            description="Restrict results to history records with this outcome status.",
        ),
    ] = None,
    predicted_class: Annotated[
        str | None,
        Query(description="Restrict results to history records with this final predicted class."),
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
        Query(
            ge=0.0,
            le=100.0,
            description="Restrict results to records with final confidence >= this percentage.",
        ),
    ] = None,
    max_confidence: Annotated[
        float | None,
        Query(
            ge=0.0,
            le=100.0,
            description="Restrict results to records with final confidence <= this percentage.",
        ),
    ] = None,
):
    """Return one page of the authenticated user's own prediction history, newest first.

    Builds an already-validated `PredictionHistoryPageRequest` and
    `PredictionHistoryFilter` from the query parameters above, then
    delegates entirely to `PredictionHistoryService.list_history_page()`,
    scoped to `current_user.id`. No business logic, filtering, or
    ownership verification is performed in this router beyond passing
    the authenticated user's own identifier through -- ownership is
    enforced by the service/repository (ADR-034/ADR-035).
    """
    user_id = str(current_user.id)

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
        "Prediction history retrieval requested: user_id=%s page=%d page_size=%d filtered=%s",
        user_id,
        page_request.page,
        page_request.page_size,
        not filters.is_empty,
    )

    page_result = await history_service.list_history_page(
        user_id=user_id,
        page_request=page_request,
        filters=filters,
    )

    logger.info(
        "Prediction history retrieval completed: user_id=%s record_count=%d total_records=%d",
        user_id,
        len(page_result.items),
        page_result.metadata.total_records,
    )

    items = [_build_history_item(record) for record in page_result.items]
    pagination = PredictionHistoryPaginationSchema(**page_result.metadata.model_dump())
    response_data = PredictionHistoryListResponseSchema(
        items=items, count=len(items), pagination=pagination
    )

    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Prediction history retrieved successfully.",
    )
