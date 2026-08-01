"""Prediction Response Builder (Phase 4.8.1, ADR-028).

`PredictionResponseBuilder` is the dedicated layer that transforms the
`FinalPredictionResult` produced by the Final Prediction Builder (Phase
4.7.4 / ADR-027) into a reusable `PredictionResponseResult`, ready for
future public API response formatting (Phase 4.8.2 onward).

Per ADR-028, this phase introduces ONLY the Response Builder
architecture:
    - Accepts `FinalPredictionResult`.
    - Exposes a single public method, `build`.
    - Copies the predicted class, confidence, and agreement/model
      bookkeeping verbatim into a `PredictionResponseResult`.

This phase performs NO additional calculations, NO confidence
modification, NO agreement recalculation, and NO runtime statistics
attachment. It never communicates with `AIRuntimeManager`,
`PredictionEngine`, `PredictionService`, or TensorFlow models --
consistent with `FinalPredictionBuilder` (ADR-027), it consumes only the
result produced upstream.
"""

from app.core.logging import get_logger
from app.ml.ensemble.final_prediction_result import FinalPredictionResult
from app.ml.response.exceptions import InvalidResponseInputError
from app.ml.response.response_result import PredictionResponseResult

logger = get_logger(__name__)


class PredictionResponseBuilder:
    """Builds a `PredictionResponseResult` from a `FinalPredictionResult`.

    Stateless and side-effect free beyond logging. Holds no per-request
    state between calls, so a single instance may be reused, or
    constructed, per request -- mirroring the same convention already
    used by `FinalPredictionBuilder`.

    Future phases extend this class without changing its public surface:
        - Phase 4.8.1: Response Builder Architecture (this phase)
        - Phase 4.8.2: PredictionService Response Integration
        - Phase 4.8.3: Response Metadata & Runtime Statistics
    """

    def build(self, final_prediction_result: FinalPredictionResult) -> PredictionResponseResult:
        """Build a `PredictionResponseResult` from a `FinalPredictionResult`.

        Args:
            final_prediction_result: The complete output of the Final
                Prediction Builder for a single uploaded image.

        Returns:
            The `PredictionResponseResult` for this request. Every field
            is copied directly from `final_prediction_result` -- no
            calculations, confidence modification, agreement
            recalculation, or runtime statistics attachment are performed
            (ADR-028).

        Raises:
            InvalidResponseInputError: If `final_prediction_result` is not
                a valid `FinalPredictionResult` instance.
        """
        self._validate(final_prediction_result)

        response_result = PredictionResponseResult(
            predicted_class=final_prediction_result.predicted_class,
            confidence=final_prediction_result.confidence,
            agreement_ratio=final_prediction_result.agreement_ratio,
            successful_models=list(final_prediction_result.successful_models),
            failed_models=list(final_prediction_result.failed_models),
            participating_models=final_prediction_result.participating_models,
        )

        logger.info(
            "Prediction response built: predicted_class=%s confidence=%.4f "
            "agreement_ratio=%.4f participating_models=%d.",
            response_result.predicted_class,
            response_result.confidence,
            response_result.agreement_ratio,
            response_result.participating_models,
        )

        return response_result

    @staticmethod
    def _validate(final_prediction_result: FinalPredictionResult) -> None:
        """Validate the type of a supplied `FinalPredictionResult`.

        Raises:
            InvalidResponseInputError: If `final_prediction_result` is not
                a `FinalPredictionResult` instance.
        """
        if not isinstance(final_prediction_result, FinalPredictionResult):
            raise InvalidResponseInputError(
                "PredictionResponseBuilder requires a FinalPredictionResult instance."
            )
