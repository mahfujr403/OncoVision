"""Prediction History Filters (Phase 5.4, ADR-035).

`PredictionHistoryFilter` is the immutable, validated domain object that
carries every optional filter criterion a caller may apply to Prediction
History retrieval. It is constructed once by the Prediction History
Router from validated query parameters and passed straight through
`PredictionHistoryService` to `PredictionHistoryRepository` -- neither
layer inspects or mutates individual fields; only the repository
translates them into SQL predicates (ADR-035).

Every field is optional so a caller may supply zero, one, or several
filters at once. Cross-field validation (`start_date <= end_date`,
`min_confidence <= max_confidence`) happens once, at construction time,
so no downstream layer needs to re-validate a `PredictionHistoryFilter`
it has already received.

Per ADR-035, filtering must never bypass ownership validation: this
model carries no `user_id` field of its own -- ownership is always
supplied separately and enforced independently by the repository query
(`PredictionHistoryRepository.list_by_user()` /
`.count_by_user()`), the same way it already is for the unfiltered
Phase 5.3 retrieval path.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.history.enums import PredictionHistoryStatus


class PredictionHistoryFilter(BaseModel):
    """Immutable set of optional filter criteria for Prediction History retrieval.

    Every field defaults to `None`, meaning "no constraint on this
    dimension" -- an all-`None` instance (`PredictionHistoryFilter()`)
    applies no filtering at all, equivalent to the Phase 5.3 unfiltered
    retrieval path.
    """

    model_config = ConfigDict(frozen=True)

    status: PredictionHistoryStatus | None = Field(
        default=None,
        description="Restrict results to history records with this outcome status.",
    )
    predicted_class: str | None = Field(
        default=None,
        description="Restrict results to history records with this final predicted class.",
    )
    start_date: datetime | None = Field(
        default=None,
        description="Restrict results to records created on or after this timestamp (inclusive).",
    )
    end_date: datetime | None = Field(
        default=None,
        description="Restrict results to records created on or before this timestamp (inclusive).",
    )
    min_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Restrict results to records with final confidence >= this percentage.",
    )
    max_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Restrict results to records with final confidence <= this percentage.",
    )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "PredictionHistoryFilter":
        """Reject filter combinations whose range bounds are internally inconsistent."""
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must not be later than end_date.")

        if (
            self.min_confidence is not None
            and self.max_confidence is not None
            and self.min_confidence > self.max_confidence
        ):
            raise ValueError("min_confidence must not be greater than max_confidence.")

        return self

    @property
    def is_empty(self) -> bool:
        """Return `True` when no filter criterion is set (no query predicates to apply)."""
        return all(
            value is None
            for value in (
                self.status,
                self.predicted_class,
                self.start_date,
                self.end_date,
                self.min_confidence,
                self.max_confidence,
            )
        )
