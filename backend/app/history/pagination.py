"""Prediction History Pagination (Phase 5.4, ADR-035).

Three small, immutable value objects support page-based Prediction
History retrieval:

    - `PredictionHistoryPageRequest`: a validated `page`/`page_size` pair,
      built once by the Prediction History Router from query parameters
      and converted into a `limit`/`offset` pair for the repository --
      mirroring the `limit`/`offset` contract `PredictionHistoryRepository`
      already exposed as of Phase 5.3.
    - `PredictionHistoryPageMetadata`: the pagination metadata (
      `current_page`, `page_size`, `total_records`, `total_pages`,
      `has_next`, `has_previous`) `PredictionHistoryService` derives from
      a `PredictionHistoryPageRequest` and the repository's total record
      count, per ADR-035's Pagination rules.
    - `PredictionHistoryPage`: the combined result of one paginated
      retrieval -- a page of `PredictionHistory` items plus its
      `PredictionHistoryPageMetadata` -- returned by
      `PredictionHistoryService.list_history_page()`.

None of these objects perform database access, filtering, or ownership
validation themselves; they are pure value objects consumed by the
service/repository/router layers (ADR-032/ADR-035).
"""

from pydantic import BaseModel, ConfigDict, Field

from app.history.prediction_history import PredictionHistory

DEFAULT_PAGE: int = 1
DEFAULT_PAGE_SIZE: int = 20
MIN_PAGE_SIZE: int = 1
MAX_PAGE_SIZE: int = 100


class PredictionHistoryPageRequest(BaseModel):
    """Immutable, validated `page`/`page_size` pair for one retrieval request."""

    model_config = ConfigDict(frozen=True)

    page: int = Field(
        default=DEFAULT_PAGE,
        ge=1,
        description="1-indexed page number to retrieve.",
    )
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        description="Maximum number of records to return for this page.",
    )

    @property
    def limit(self) -> int:
        """Return the repository-facing `limit` implied by `page_size`."""
        return self.page_size

    @property
    def offset(self) -> int:
        """Return the repository-facing `offset` implied by `page` and `page_size`."""
        return (self.page - 1) * self.page_size


class PredictionHistoryPageMetadata(BaseModel):
    """Immutable pagination metadata describing one retrieved page."""

    model_config = ConfigDict(frozen=True)

    current_page: int = Field(description="The page number this metadata describes.")
    page_size: int = Field(description="Maximum number of records requested for this page.")
    total_records: int = Field(
        description="Total number of records matching the request, across every page."
    )
    total_pages: int = Field(description="Total number of pages available for this request.")
    has_next: bool = Field(description="Whether a page after `current_page` exists.")
    has_previous: bool = Field(description="Whether a page before `current_page` exists.")

    @classmethod
    def from_totals(
        cls,
        page_request: PredictionHistoryPageRequest,
        total_records: int,
    ) -> "PredictionHistoryPageMetadata":
        """Derive pagination metadata from a page request and a repository-reported total.

        Performs only arithmetic already implied by `page_request` and
        `total_records` -- never re-queries the database itself.
        """
        total_pages = (
            (total_records + page_request.page_size - 1) // page_request.page_size
            if total_records > 0
            else 0
        )

        return cls(
            current_page=page_request.page,
            page_size=page_request.page_size,
            total_records=total_records,
            total_pages=total_pages,
            has_next=page_request.page < total_pages,
            has_previous=page_request.page > 1 and total_records > 0,
        )


class PredictionHistoryPage(BaseModel):
    """Immutable combined result of one paginated, optionally filtered retrieval."""

    model_config = ConfigDict(frozen=True)

    items: list[PredictionHistory] = Field(
        description="The `PredictionHistory` records on this page, newest first."
    )
    metadata: PredictionHistoryPageMetadata = Field(
        description="Pagination metadata describing this page relative to the full result set."
    )
