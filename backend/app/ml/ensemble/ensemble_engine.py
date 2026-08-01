"""Centralized Adaptive Ensemble Engine (ADR-009) and Phase 4.7.1 Adaptive
Ensemble Integration entry point (ADR-024).

This module contains two, intentionally independent engines:

    - `AdaptiveEnsembleEngine` (Phase 3.4, ADR-009): consumes
      `PredictionEngineResult` objects produced directly by the
      Prediction Engine (ADR-008) and produces a single, fault-tolerant
      *final* ensemble prediction (voting, confidence aggregation,
      agreement scoring). Never communicates with TensorFlow, the AI
      Runtime Manager, or the database; consumes only prediction results.

    - `EnsembleEngine` (Phase 4.7.1, ADR-024): the Adaptive Ensemble
      Integration entry point for the Phase 4.x Prediction API pipeline.
      Consumes an `EnsembleRequest` built from the standardized
      `PredictionExecutionResult` (ADR-022), validates it, separates
      accepted (successful) predictions from rejected (failed) ones, and
      returns an `EnsembleResult` ready for future voting. Performs NO
      voting, NO confidence calculation, and NO final prediction
      selection -- those responsibilities begin in Phase 4.7.2 onward.

Neither engine replaces the other in this phase; Phase 4.7.1 only
introduces the validation/preparation entry point described by ADR-024.
`PredictionService` (Phase 4.4/4.7) is wired to `EnsembleEngine`.
"""

from app.core.logging import get_logger
from app.ml.ensemble.decision import EnsembleDecisionMaker
from app.ml.ensemble.ensemble_request import EnsembleRequest
from app.ml.ensemble.ensemble_result import EnsembleResult, EnsembleStatus, ValidationSummary
from app.ml.ensemble.exceptions import InvalidEnsembleInputError, PredictionUnavailableError
from app.ml.ensemble.response import EnsemblePredictionResult
from app.ml.prediction.prediction_result import PredictionEngineResult
from app.ml.registry.model_registry import ModelRegistry
from app.utils.environment import get_current_timestamp

logger = get_logger(__name__)


class AdaptiveEnsembleEngine:
    """Combines individual model predictions into a single ensemble prediction.

    The Ensemble Engine automatically detects available models, ignores
    failed models, and dynamically selects an ensemble strategy based on
    how many models executed successfully (Project Context, Section 18-19).
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry
        self._decision_maker = EnsembleDecisionMaker(registry)

    def generate_ensemble_prediction(
        self, engine_result: PredictionEngineResult
    ) -> EnsemblePredictionResult:
        """Produce a final ensemble prediction from a Prediction Engine result.

        Args:
            engine_result: The complete output of the Prediction Engine for
                a single uploaded image, containing successful individual
                predictions and any failed models.

        Returns:
            The final `EnsemblePredictionResult`, using every successfully
            executed model.

        Raises:
            PredictionUnavailableError: If no model produced a successful
                prediction (Case 4 of the Ensemble Decision Strategy).
        """
        if not engine_result.predictions:
            logger.warning(
                "Ensemble prediction unavailable: 0/%d models produced a successful prediction.",
                len(engine_result.failed_models),
            )
            raise PredictionUnavailableError()

        decision = self._decision_maker.decide(engine_result.predictions)

        logger.info(
            "Ensemble decision resolved via '%s' using %d/%d executed models: "
            "label='%s' confidence=%.2f%% agreement=%s.",
            decision.ensemble_strategy.value,
            len(engine_result.predictions),
            len(engine_result.predictions) + len(engine_result.failed_models),
            decision.final_label,
            decision.confidence.final_confidence_percentage,
            decision.agreement.agreement_level.value,
        )

        return EnsemblePredictionResult(
            final_label=decision.final_label,
            final_class_index=decision.final_class_index,
            confidence=decision.confidence,
            agreement=decision.agreement,
            ensemble_strategy=decision.ensemble_strategy,
            executed_models=engine_result.predictions,
            failed_models=engine_result.failed_models,
            model_contributions=decision.model_contributions,
            prediction_timestamp=get_current_timestamp(),
        )


class EnsembleEngine:
    """Phase 4.7.1 Adaptive Ensemble Integration entry point (ADR-024).

    The single entry point through which the Phase 4.x Prediction API
    pipeline (`PredictionService`) reaches the Adaptive Ensemble layer.
    Accepts an `EnsembleRequest` built exclusively from a standardized
    `PredictionExecutionResult` (ADR-022), validates it, separates
    accepted (successful) predictions from rejected (failed) ones, and
    returns an `EnsembleResult` ready for future voting.

    Stateless and side-effect free beyond logging: performs no AI
    inference, no I/O, and never communicates with `AIRuntimeManager`,
    `PredictionEngine`, or TensorFlow models -- consistent with
    `AdaptiveEnsembleEngine` above and ADR-009.

    Per ADR-024, this phase performs NO voting, NO confidence
    calculation, and NO final prediction selection. Future ensemble
    phases extend this class without changing its public surface:
        - Phase 4.7.2: Voting & Agreement Engine
        - Phase 4.7.3: Confidence Calibration
        - Phase 4.7.4: Final Prediction Builder
    """

    def process(self, request: EnsembleRequest) -> EnsembleResult:
        """Validate `request` and prepare its predictions for future voting.

        Args:
            request: The standardized `EnsembleRequest` for this prediction
                request (`EnsembleRequest.from_execution_result`).

        Returns:
            A validated `EnsembleResult` describing every accepted
            (successful) and rejected (failed) model prediction, ready for
            future ensemble processing.

        Raises:
            PredictionUnavailableError: If the supplied
                `PredictionExecutionResult` has zero successful
                predictions. This is a fault-tolerance boundary (ADR-005),
                not a structural validation error -- it only fires once
                every individual model has already failed.
            InvalidEnsembleInputError: If the request is structurally
                invalid -- a missing `PredictionExecutionResult`, missing
                runtime metadata, or missing execution statistics.
        """
        logger.info("Ensemble started: request_id=%s", request.request_id)

        validation_summary = self._validate(request)

        accepted_predictions = request.execution_result.individual_predictions
        rejected_predictions = request.execution_result.failed_model_predictions
        successful_models = [prediction.model_id for prediction in accepted_predictions]
        failed_models = [prediction.model_id for prediction in rejected_predictions]

        ensemble_status = (
            EnsembleStatus.DEGRADED if rejected_predictions else EnsembleStatus.READY_FOR_VOTING
        )

        logger.info(
            "Predictions accepted: request_id=%s count=%d models=[%s]",
            request.request_id,
            len(accepted_predictions),
            ", ".join(successful_models),
        )
        logger.info(
            "Predictions rejected: request_id=%s count=%d models=[%s]",
            request.request_id,
            len(rejected_predictions),
            ", ".join(failed_models),
        )
        logger.info(
            "Successful models: request_id=%s models=[%s]",
            request.request_id,
            ", ".join(successful_models),
        )
        logger.info(
            "Failed models: request_id=%s models=[%s]",
            request.request_id,
            ", ".join(failed_models),
        )

        result = EnsembleResult(
            request_id=request.request_id,
            accepted_predictions=accepted_predictions,
            rejected_predictions=rejected_predictions,
            successful_models=successful_models,
            failed_models=failed_models,
            ensemble_status=ensemble_status,
            validation_summary=validation_summary,
        )

        logger.info(
            "Ensemble preparation completed: request_id=%s status=%s "
            "accepted_count=%d rejected_count=%d",
            request.request_id,
            ensemble_status.value,
            len(accepted_predictions),
            len(rejected_predictions),
        )
        return result

    @staticmethod
    def _validate(request: EnsembleRequest) -> ValidationSummary:
        """Run every Phase 4.7.1 validation check against `request` (ADR-024).

        Validates, in order:
            - A `PredictionExecutionResult` is present.
            - At least one successful prediction exists.
            - Runtime metadata is present.
            - Execution statistics are present.

        Raises:
            InvalidEnsembleInputError: If the `PredictionExecutionResult`,
                runtime metadata, or execution statistics are missing --
                a structurally invalid request rather than a normal
                fault-tolerance outcome.
            PredictionUnavailableError: If the `PredictionExecutionResult`
                is present but contains zero successful predictions.
        """
        execution_result = request.execution_result
        execution_result_present = execution_result is not None

        if not execution_result_present:
            raise InvalidEnsembleInputError(
                "EnsembleRequest is missing a PredictionExecutionResult."
            )

        runtime_metadata_present = request.runtime_metadata is not None
        if not runtime_metadata_present:
            raise InvalidEnsembleInputError(
                "EnsembleRequest is missing AI Runtime metadata."
            )

        execution_statistics_present = request.execution_statistics is not None
        if not execution_statistics_present:
            raise InvalidEnsembleInputError(
                "EnsembleRequest is missing execution statistics."
            )

        has_successful_prediction = execution_result.has_any_successful_prediction()
        if not has_successful_prediction:
            raise PredictionUnavailableError(
                "Prediction unavailable: no production model returned a "
                "successful result for this request."
            )

        return ValidationSummary(
            execution_result_present=execution_result_present,
            has_successful_prediction=has_successful_prediction,
            runtime_metadata_present=runtime_metadata_present,
            execution_statistics_present=execution_statistics_present,
            validation_message=(
                "EnsembleRequest passed validation: PredictionExecutionResult, "
                "runtime metadata, and execution statistics are present, with "
                "at least one successful prediction."
            ),
        )
