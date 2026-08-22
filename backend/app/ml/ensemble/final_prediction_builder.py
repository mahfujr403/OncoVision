"""Final Prediction Builder (Phase 4.7.4, ADR-027).

`FinalPredictionBuilder` is the dedicated layer that transforms the
`CalibratedEnsembleResult` produced by the Confidence Calibration Engine
(Phase 4.7.3 / ADR-026) into a reusable `FinalPredictionResult`, ready for
the future Response Builder (Phase 4.8).

Per ADR-027, this phase introduces ONLY the final prediction architecture:
    - Accepts `CalibratedEnsembleResult`.
    - Exposes a single public method, `build`.
    - Copies the winning class, calibrated confidence, and agreement
      statistics verbatim into a `FinalPredictionResult`.

This phase performs NO additional calculations, NO confidence
modification, and NO vote-score modification. It never communicates with
`AIRuntimeManager`, `PredictionEngine`, `PredictionService`, or
TensorFlow models -- consistent with `ConfidenceCalibrationEngine`
(ADR-026), it consumes only the result produced upstream.

Phase 4.7.4 Update (Unknown-Input Guard): `build` optionally accepts the
same per-model `IndividualPrediction` list the Prediction Engine produced
for this request. When supplied, `predicted_class` is overridden to
`"unknown"` whenever either of two low-confidence conditions holds:
    - The calibrated combined confidence is below 92%.
    - Any single participating model's own top-class confidence is
      below 80%.
This exists so an off-domain image (e.g. a non-lung histopathology
slide) that happens to land near a decision boundary for every model
individually is never reported as a confident, specific diagnosis --
"unknown" is reported instead. `individual_predictions` defaults to
`None`, in which case this guard is skipped entirely and `build` behaves
exactly as before (ADR-027 baseline), preserving backward compatibility
for any caller that has not been updated to supply it.
"""

from app.core.logging import get_logger
from app.ml.ensemble.calibration_result import CalibratedEnsembleResult
from app.ml.ensemble.exceptions import InvalidEnsembleInputError
from app.ml.ensemble.final_prediction_result import FinalPredictionResult
from app.ml.prediction.prediction_result import IndividualPrediction

logger = get_logger(__name__)

UNKNOWN_PREDICTED_CLASS = "unknown"

# Below either threshold, the ensemble result is too unreliable to report
# as a specific class -- most often the signature of an off-domain image
# (e.g. a non-lung histopathology slide) rather than a genuine diagnosis.
_MIN_COMBINED_CONFIDENCE_PERCENTAGE = 92.0
_MIN_INDIVIDUAL_CONFIDENCE_PERCENTAGE = 80.0


class FinalPredictionBuilder:
    """Builds a `FinalPredictionResult` from a `CalibratedEnsembleResult`.

    Stateless and side-effect free beyond logging. Holds no per-request
    state between calls, so a single instance may be reused, or
    constructed, per request -- mirroring the same convention already
    used by `ConfidenceCalibrationEngine`.

    Future phases extend this class without changing its public surface:
        - Phase 4.7.4: Final Prediction Builder (this phase)
        - Phase 4.8: Response Builder
    """

    def build(
        self,
        calibrated_result: CalibratedEnsembleResult,
        individual_predictions: list[IndividualPrediction] | None = None,
    ) -> FinalPredictionResult:
        """Build a `FinalPredictionResult` from a `CalibratedEnsembleResult`.

        Args:
            calibrated_result: The complete output of the Confidence
                Calibration Engine for a single uploaded image.
            individual_predictions: The same successfully-executed
                models' `IndividualPrediction` list the Prediction Engine
                produced for this request, used only to evaluate the
                unknown-input guard described above. `None` (the
                default) skips the guard entirely.

        Returns:
            The `FinalPredictionResult` for this request. Every field is
            copied directly from `calibrated_result` -- no calculations,
            confidence modification, or vote-score modification are
            performed (ADR-027) -- except `predicted_class`, which is
            overridden to `"unknown"` when `individual_predictions` is
            supplied and either low-confidence condition above holds.

        Raises:
            InvalidEnsembleInputError: If `calibrated_result` is not a
                valid `CalibratedEnsembleResult` instance.
        """
        self._validate(calibrated_result)

        agreement_statistics = calibrated_result.agreement_statistics
        predicted_class = calibrated_result.winning_class

        if predicted_class is not None and individual_predictions:
            predicted_class = self._apply_unknown_guard(
                predicted_class=predicted_class,
                combined_confidence_percentage=calibrated_result.calibrated_confidence,
                individual_predictions=individual_predictions,
            )

        final_result = FinalPredictionResult(
            predicted_class=predicted_class,
            confidence=calibrated_result.calibrated_confidence,
            agreement_ratio=agreement_statistics.agreement_ratio,
            successful_models=list(agreement_statistics.successful_models),
            failed_models=list(agreement_statistics.failed_models),
            participating_models=agreement_statistics.total_models,
        )

        logger.info(
            "Final prediction built: predicted_class=%s confidence=%.4f "
            "agreement_ratio=%.4f participating_models=%d.",
            final_result.predicted_class,
            final_result.confidence,
            final_result.agreement_ratio,
            final_result.participating_models,
        )

        return final_result

    @staticmethod
    def _apply_unknown_guard(
        predicted_class: str,
        combined_confidence_percentage: float,
        individual_predictions: list[IndividualPrediction],
    ) -> str:
        """Return `"unknown"` in place of `predicted_class` when either guard condition holds.

        Args:
            predicted_class: The winning class label that would otherwise
                be reported.
            combined_confidence_percentage: The calibrated ensemble
                confidence percentage for `predicted_class`.
            individual_predictions: Every successfully-executed model's
                own `IndividualPrediction` for this request.

        Returns:
            `"unknown"` if the combined confidence is below
            `_MIN_COMBINED_CONFIDENCE_PERCENTAGE` or any individual
            model's own top-class confidence is below
            `_MIN_INDIVIDUAL_CONFIDENCE_PERCENTAGE`; otherwise
            `predicted_class`, unchanged.
        """
        combined_confidence_too_low = (
            combined_confidence_percentage < _MIN_COMBINED_CONFIDENCE_PERCENTAGE
        )
        weakest_individual_confidence = min(
            prediction.confidence.confidence_percentage for prediction in individual_predictions
        )
        an_individual_confidence_too_low = (
            weakest_individual_confidence < _MIN_INDIVIDUAL_CONFIDENCE_PERCENTAGE
        )

        if not (combined_confidence_too_low or an_individual_confidence_too_low):
            return predicted_class

        logger.info(
            "Unknown-input guard triggered: original_predicted_class=%s "
            "combined_confidence=%.4f (min=%.1f, too_low=%s) "
            "weakest_individual_confidence=%.4f (min=%.1f, too_low=%s).",
            predicted_class,
            combined_confidence_percentage,
            _MIN_COMBINED_CONFIDENCE_PERCENTAGE,
            combined_confidence_too_low,
            weakest_individual_confidence,
            _MIN_INDIVIDUAL_CONFIDENCE_PERCENTAGE,
            an_individual_confidence_too_low,
        )
        return UNKNOWN_PREDICTED_CLASS

    @staticmethod
    def _validate(calibrated_result: CalibratedEnsembleResult) -> None:
        """Validate the type of a supplied `CalibratedEnsembleResult`.

        Raises:
            InvalidEnsembleInputError: If `calibrated_result` is not a
                `CalibratedEnsembleResult` instance.
        """
        if not isinstance(calibrated_result, CalibratedEnsembleResult):
            raise InvalidEnsembleInputError(
                "FinalPredictionBuilder requires a CalibratedEnsembleResult instance."
            )
