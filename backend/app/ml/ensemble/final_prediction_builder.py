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
"""

from app.core.logging import get_logger
from app.ml.ensemble.calibration_result import CalibratedEnsembleResult
from app.ml.ensemble.exceptions import InvalidEnsembleInputError
from app.ml.ensemble.final_prediction_result import FinalPredictionResult

logger = get_logger(__name__)


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

    def build(self, calibrated_result: CalibratedEnsembleResult) -> FinalPredictionResult:
        """Build a `FinalPredictionResult` from a `CalibratedEnsembleResult`.

        Args:
            calibrated_result: The complete output of the Confidence
                Calibration Engine for a single uploaded image.

        Returns:
            The `FinalPredictionResult` for this request. Every field is
            copied directly from `calibrated_result` -- no calculations,
            confidence modification, or vote-score modification are
            performed (ADR-027).

        Raises:
            InvalidEnsembleInputError: If `calibrated_result` is not a
                valid `CalibratedEnsembleResult` instance.
        """
        self._validate(calibrated_result)

        agreement_statistics = calibrated_result.agreement_statistics
        final_result = FinalPredictionResult(
            predicted_class=calibrated_result.winning_class,
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
