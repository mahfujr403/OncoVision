"""Prediction History Mapper (Phase 5.1, ADR-032).

`PredictionHistoryMapper` is the dedicated layer that transforms an
already-completed `app.services.prediction_result.PredictionResult` and
its originating `app.services.prediction_context.PredictionContext` into
an immutable `PredictionHistory` record, ready for future persistence
(Phase 5.2 / ADR-033).

Per ADR-032, Prediction History remains completely independent from the
Prediction Engine: this module performs NO inference, NO preprocessing,
NO ensemble voting, and NO confidence recalculation. Every value on the
resulting `PredictionHistory` is copied -- directly or through a simple
per-field projection -- from fields the prediction pipeline already
computed:
    - `PredictionResult.response_result`
      (`app.ml.response.response_result.PredictionResponseResult`, ADR-028)
    - `PredictionResult.individual_model_results`
      (`app.ml.prediction.prediction_result.IndividualPrediction`, ADR-008)
    - `PredictionResult.execution_stats`
      (`app.ml.prediction.prediction_result.PredictionExecutionStats`, ADR-023)
    - `PredictionResult.runtime_statistics`
      (`app.services.runtime_metadata.RuntimeMetadata`, ADR-016)
    - `PredictionContext` (request/user/image metadata, ADR-013)

This phase introduces the mapping architecture only. `PredictionHistoryMapper`
is not yet wired into `PredictionService` or the Prediction Router -- that
begins with history persistence (Phase 5.2).
"""

from app.core.logging import get_logger
from app.history.enums import PredictionHistoryStatus
from app.history.exceptions import InvalidHistoryInputError
from app.history.metadata import PredictionHistoryMetadata
from app.history.prediction_history import PredictionHistory
from app.history.summary import PredictionHistoryModelEntry, PredictionHistorySummary
from app.ml.prediction.prediction_result import IndividualPrediction
from app.ml.response.response_result import PredictionResponseResult
from app.services.prediction_context import PredictionContext
from app.services.prediction_result import PredictionResult
from app.utils.environment import generate_request_id, get_current_timestamp

logger = get_logger(__name__)


class PredictionHistoryMapper:
    """Builds an immutable `PredictionHistory` from a completed prediction run.

    Stateless and side-effect free beyond logging. Holds no per-request
    state between calls, so a single instance may be reused, or
    constructed, per request -- mirroring the same convention already
    used by `PredictionResponseBuilder` and `FinalPredictionBuilder`.
    """

    def to_history(
        self,
        prediction_result: PredictionResult,
        context: PredictionContext,
    ) -> PredictionHistory:
        """Build a `PredictionHistory` record from a completed prediction run.

        Args:
            prediction_result: The service-layer outcome of
                `PredictionService.predict()` for a single request.
            context: The `PredictionContext` that originated `prediction_result`.

        Returns:
            An immutable `PredictionHistory`, ready to be handed to a
            future `PredictionHistoryRepository` implementation
            (Phase 5.2). This record is never persisted by this method.

        Raises:
            InvalidHistoryInputError: If `prediction_result` or `context`
                is not an instance of the expected type.
        """
        self._validate(prediction_result, context)

        response_result: PredictionResponseResult | None = prediction_result.response_result
        individual_model_results: list[IndividualPrediction] | None = (
            prediction_result.individual_model_results
        )

        metadata = self._build_metadata(prediction_result, context)
        summary = self._build_summary(response_result, individual_model_results)
        status = self._resolve_status(response_result)

        history = PredictionHistory(
            history_id=generate_request_id(),
            request_id=prediction_result.request_id,
            user_id=context.user_id,
            status=status,
            created_at=get_current_timestamp(),
            metadata=metadata,
            summary=summary,
        )

        logger.info(
            "Prediction history record prepared: history_id=%s request_id=%s "
            "status=%s (not persisted -- Phase 5.2).",
            history.history_id,
            history.request_id,
            history.status.value,
        )

        return history

    @staticmethod
    def _validate(prediction_result: PredictionResult, context: PredictionContext) -> None:
        """Validate the types of the supplied mapper inputs.

        Raises:
            InvalidHistoryInputError: If either argument is not an
                instance of its expected type.
        """
        if not isinstance(prediction_result, PredictionResult):
            raise InvalidHistoryInputError(
                "PredictionHistoryMapper requires a PredictionResult instance."
            )
        if not isinstance(context, PredictionContext):
            raise InvalidHistoryInputError(
                "PredictionHistoryMapper requires a PredictionContext instance."
            )

    @staticmethod
    def _build_metadata(
        prediction_result: PredictionResult,
        context: PredictionContext,
    ) -> PredictionHistoryMetadata:
        """Build the request/image metadata snapshot for this history record."""
        runtime_metadata = prediction_result.runtime_statistics
        execution_stats = prediction_result.execution_stats

        return PredictionHistoryMetadata(
            request_id=context.request_id,
            requested_at=context.requested_at,
            user_id=context.user_id,
            user_email=context.user_email,
            image_filename=context.image_filename,
            image_content_type=context.image_content_type,
            image_size_bytes=context.image_size_bytes,
            image_width=context.image_width,
            image_height=context.image_height,
            model_manifest_version=getattr(runtime_metadata, "manifest_version", None),
            processing_time_ms=getattr(execution_stats, "total_execution_time_ms", None),
        )

    @staticmethod
    def _build_summary(
        response_result: PredictionResponseResult | None,
        individual_model_results: list[IndividualPrediction] | None,
    ) -> PredictionHistorySummary:
        """Build the ensemble-level and per-model summary for this history record."""
        entries = [
            PredictionHistoryModelEntry(
                model_name=prediction.model_name,
                prediction=prediction.predicted_label,
                confidence=prediction.confidence.confidence_percentage,
                inference_time_ms=prediction.inference_time_ms,
            )
            for prediction in (individual_model_results or [])
        ]

        if response_result is None:
            summary = PredictionHistorySummary.empty()
            return summary.model_copy(update={"individual_predictions": entries})

        return PredictionHistorySummary(
            predicted_class=response_result.predicted_class,
            confidence=response_result.confidence,
            agreement_ratio=response_result.agreement_ratio,
            successful_models=list(response_result.successful_models),
            failed_models=list(response_result.failed_models),
            participating_models=response_result.participating_models,
            individual_predictions=entries,
        )

    @staticmethod
    def _resolve_status(
        response_result: PredictionResponseResult | None,
    ) -> PredictionHistoryStatus:
        """Derive this record's `PredictionHistoryStatus` from the response result.

        Mirrors the Ensemble Decision Strategy (Project Context, Section
        19 / ADR-009): a predicted class with no failed models is a full
        `SUCCESS`; a predicted class alongside one or more failed models
        is a `PARTIAL_SUCCESS`; no predicted class and no participating
        models is `FAILED`. The RESPONSE pipeline stage never having
        completed is `PENDING`.
        """
        if response_result is None:
            return PredictionHistoryStatus.PENDING
        if response_result.predicted_class is None:
            return PredictionHistoryStatus.FAILED
        if response_result.failed_models:
            return PredictionHistoryStatus.PARTIAL_SUCCESS
        return PredictionHistoryStatus.SUCCESS
