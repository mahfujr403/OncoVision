"""Prediction History domain model (Phase 5.1, ADR-032).

`PredictionHistory` is the immutable domain object representing a single
completed prediction request, ready for future persistence (Phase 5.2 /
ADR-033). Per ADR-032, Prediction History records are append-only:
`PredictionHistory` is frozen so no code path can mutate a record after
`PredictionHistoryMapper` builds it.

This phase introduces the domain shape only. No database table, ORM
mapping, or persistence mechanism exists yet -- that begins with the
`PredictionHistoryRepository` implementation in Phase 5.2.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.history.enums import PredictionHistoryStatus
from app.history.metadata import PredictionHistoryMetadata
from app.history.summary import PredictionHistorySummary


class PredictionHistory(BaseModel):
    """Immutable, append-only record of a single completed prediction request.

    Constructed exactly once per request by `PredictionHistoryMapper` from
    an already-completed `app.services.prediction_result.PredictionResult`
    and its originating `app.services.prediction_context.PredictionContext`.
    Never constructed, mutated, or recalculated by any other component
    (ADR-032).
    """

    model_config = ConfigDict(frozen=True)

    history_id: str = Field(
        description="Unique identifier for this history record, distinct from `request_id`."
    )
    request_id: str = Field(
        description="Identifier of the prediction request this record describes."
    )
    user_id: str = Field(
        description="Unique identifier of the user who owns this history record."
    )
    status: PredictionHistoryStatus = Field(
        description="Outcome of the prediction pipeline run this record describes."
    )
    created_at: str = Field(
        description="ISO 8601 timestamp of when this history record was prepared."
    )
    metadata: PredictionHistoryMetadata = Field(
        description="Request-scoped and image-scoped metadata for this record."
    )
    summary: PredictionHistorySummary = Field(
        description="Ensemble-level prediction summary for this record."
    )

    @classmethod
    def empty(
        cls,
        history_id: str,
        request_id: str,
        user_id: str,
        created_at: str,
        metadata: PredictionHistoryMetadata,
    ) -> "PredictionHistory":
        """Return a `PredictionHistory` with `PENDING` status and an empty summary.

        The correct record for a `PredictionResult` whose pipeline did not
        reach the RESPONSE stage -- mirrors `PredictionHistorySummary.empty()`.
        """
        return cls(
            history_id=history_id,
            request_id=request_id,
            user_id=user_id,
            status=PredictionHistoryStatus.PENDING,
            created_at=created_at,
            metadata=metadata,
            summary=PredictionHistorySummary.empty(),
        )
