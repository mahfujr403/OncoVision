"""Administration API response schemas (Phase 7, ADR-036).

Defines the public response contract for every endpoint under
`app.api.v1.admin`. Follows the same convention already established by
`app.api.v1.history.responses`: every field here is copied directly from
an already-computed domain object (`app.models.user.User`,
`app.history.prediction_history.PredictionHistory`) or an existing
service's return value -- this module performs no calculation of its own.

`AdminPaginationSchema` intentionally duplicates the shape of
`app.api.v1.history.responses.PredictionHistoryPaginationSchema` rather
than importing it: the two describe pagination for entirely different
resources (users vs. history records), and every other domain in this
codebase (`app.history.pagination`, `app.reports`) already defines its
own pagination schema rather than sharing one across domains.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.api.v1.history.responses import (
    PredictionHistoryModelEntrySchema,
    PredictionHistoryStatus,
)
from app.models.enums import UserRole
from app.schemas.user import UserResponse

__all__ = [
    "AdminPaginationSchema",
    "AdminUserListResponseSchema",
    "AdminUserDetailResponseSchema",
    "AdminUserStatusChangeResponseSchema",
    "AdminHistoryItemSchema",
    "AdminHistoryListResponseSchema",
    "AdminHistoryDetailResponseSchema",
    "AdminSystemStatusSchema",
]


class AdminPaginationSchema(BaseModel):
    """Pagination metadata shared by every paginated Admin API response."""

    current_page: int = Field(description="The page number this response describes.")
    page_size: int = Field(description="Maximum number of records requested for this page.")
    total_records: int = Field(
        description="Total number of records matching the request, across every page."
    )
    total_pages: int = Field(description="Total number of pages available for this request.")
    has_next: bool = Field(description="Whether a page after `current_page` exists.")
    has_previous: bool = Field(description="Whether a page before `current_page` exists.")


class AdminUserListResponseSchema(BaseModel):
    """Response payload for `GET /api/v1/admin/users`."""

    items: list[UserResponse] = Field(description="Users on this page, newest first.")
    count: int = Field(description="Number of users included in this response.")
    pagination: AdminPaginationSchema = Field(
        description="Pagination metadata describing the full result set."
    )


class AdminUserDetailResponseSchema(UserResponse):
    """Response payload for `GET /api/v1/admin/users/{user_id}`.

    Identical to `UserResponse` -- administrators see exactly the same
    safe user projection any authenticated caller would see of their own
    account (ADR-036: administration must never expose password hashes,
    JWT secrets, or other internal security configuration).
    """


class AdminUserStatusChangeResponseSchema(BaseModel):
    """Response payload for the activate/deactivate account-status endpoints."""

    user: UserResponse = Field(description="The user record after the status change.")


class AdminHistoryItemSchema(BaseModel):
    """A single prediction history record exposed to administrators.

    Extends the shape of `app.api.v1.history.responses.PredictionHistoryItemSchema`
    with `user_id` -- the one field ordinary, self-service history retrieval
    never needs to expose (a user always already knows their own
    records), but administrative oversight does (ADR-036).
    """

    history_id: str = Field(description="Unique identifier of this history record.")
    request_id: str = Field(
        description="Identifier of the original prediction request this record describes."
    )
    user_id: str = Field(description="Identifier of the user who owns this history record.")
    status: PredictionHistoryStatus = Field(
        description="Outcome of the prediction pipeline run this record describes."
    )
    created_at: str = Field(
        description="ISO 8601 timestamp of when this history record was created."
    )
    image_filename: str = Field(description="Original filename of the uploaded image.")
    predicted_class: str | None = Field(description="Final predicted class, if any.")
    confidence: float = Field(description="Final calibrated confidence, as a percentage.")
    agreement_ratio: float = Field(description="Agreement ratio among participating models.")
    successful_models: list[str] = Field(description="Models that produced a valid prediction.")
    failed_models: list[str] = Field(description="Models that failed during this request.")
    participating_models: int = Field(description="Total number of models that participated.")
    individual_predictions: list[PredictionHistoryModelEntrySchema] = Field(
        description="Per-model prediction results."
    )


class AdminHistoryListResponseSchema(BaseModel):
    """Response payload for `GET /api/v1/admin/history`."""

    items: list[AdminHistoryItemSchema] = Field(
        description="History records on this page, newest first, across every user "
        "unless narrowed by `user_id`."
    )
    count: int = Field(description="Number of records included in this response.")
    pagination: AdminPaginationSchema = Field(
        description="Pagination metadata describing the full, optionally filtered result set."
    )


class AdminHistoryDetailResponseSchema(AdminHistoryItemSchema):
    """Response payload for `GET /api/v1/admin/history/{history_id}`.

    Extends `AdminHistoryItemSchema` with the same runtime/image metadata
    fields already exposed by the self-service
    `PredictionHistoryDetailResponseSchema` -- administrators see the
    complete record, scoped to no particular owner.
    """

    image_content_type: str = Field(description="Declared MIME type of the uploaded image.")
    image_size_bytes: int = Field(description="Size of the uploaded image, in bytes.")
    image_width: int = Field(description="Width of the uploaded image, in pixels.")
    image_height: int = Field(description="Height of the uploaded image, in pixels.")
    model_manifest_version: str | None = Field(
        description="Model Manifest version active when this prediction was made."
    )
    processing_time_ms: float | None = Field(
        description="Total pipeline processing time for this request, in milliseconds."
    )


class AdminSystemStatusSchema(BaseModel):
    """Response payload for `GET /api/v1/admin/system`.

    Aggregates only safe, already-computed operational metadata from
    existing services (`SystemService`, `AIRuntimeManager`,
    `check_database_connection`) -- no secrets, credentials, environment
    variables, or other sensitive infrastructure information is ever
    included (ADR-036/ADR-047).
    """

    application: dict[str, Any] = Field(description="Core application metadata.")
    database: dict[str, Any] = Field(description="Database connectivity status.")
    runtime: dict[str, Any] = Field(description="AI Runtime Manager health snapshot.")
    models: dict[str, Any] = Field(description="Per-model runtime lifecycle status.")
    generated_at: str = Field(description="ISO 8601 timestamp of when this status was generated.")


# Re-exported for router type hints without importing `app.models.enums`
# directly in every admin router module.
__all__.append("UserRole")
