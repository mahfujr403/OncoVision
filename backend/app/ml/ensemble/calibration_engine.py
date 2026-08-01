"""Confidence Calibration Engine (Phase 4.7.3, ADR-026).

`ConfidenceCalibrationEngine` consumes the `VotingResult` produced by the
Adaptive Weighted Voting Engine (Phase 4.7.2 / ADR-025) and turns it into a
fully populated `CalibratedEnsembleResult`, ready for the future Final
Prediction Builder (Phase 4.7.4).

Phase 4.7.3 is implemented in two steps (ADR-026 Update):
    - Phase 4.7.3.1: Confidence Calibration architecture (foundation only
      -- `CalibratedEnsembleResult`, `AgreementStatistics`, validation).
    - Phase 4.7.3.2: Agreement & confidence calculation (this phase) --
      winning-class selection, agreement-ratio calculation, and calibrated
      confidence calculation.

This phase performs NO final prediction selection and NO response
formatting -- those remain the responsibility of the future Final
Prediction Builder (Phase 4.7.4). `ConfidenceCalibrationEngine` never
communicates with `AIRuntimeManager`, `PredictionEngine`,
`PredictionService`, or TensorFlow models -- consistent with
`AdaptiveWeightedVotingEngine` (ADR-025), it consumes only the
`VotingResult` produced upstream.
"""

from app.core.logging import get_logger
from app.ml.ensemble.calibration_result import AgreementStatistics, CalibratedEnsembleResult
from app.ml.ensemble.exceptions import EnsembleConfigurationError, InvalidEnsembleInputError
from app.ml.ensemble.voting_result import VotingResult, WeightedVote

logger = get_logger(__name__)

_CONFIDENCE_PERCENTAGE_MULTIPLIER = 100
_ROUNDING_PRECISION = 4


class ConfidenceCalibrationEngine:
    """Turns a `VotingResult` into a fully populated `CalibratedEnsembleResult`.

    Stateless and side-effect free beyond logging. Holds no per-request
    state between calls, so a single instance may be reused, or
    constructed, per request -- mirroring the same convention already
    used by `AdaptiveWeightedVotingEngine`.

    Every calculation performed by this engine is a pure function of its
    `VotingResult` input, so results are deterministic and reusable across
    calls given the same input (ADR-026).

    Future phases extend this class without changing its public surface:
        - Phase 4.7.3: Confidence Calibration (this phase, complete)
        - Phase 4.7.4: Final Prediction Builder
    """

    def calibrate(self, voting_result: VotingResult) -> CalibratedEnsembleResult:
        """Calibrate a `VotingResult` into a fully populated `CalibratedEnsembleResult`.

        Args:
            voting_result: The complete output of the Adaptive Weighted
                Voting Engine for a single uploaded image.

        Returns:
            The `CalibratedEnsembleResult` for this request, with
            `winning_class`, `calibrated_confidence`, and
            `agreement_statistics` (including `agreement_ratio`) fully
            calculated from `voting_result`. Does not select a final
            prediction or perform response formatting (ADR-026).

        Raises:
            InvalidEnsembleInputError: If `voting_result` is not a valid
                `VotingResult` instance.
            EnsembleConfigurationError: If `voting_result`'s model
                bookkeeping is internally inconsistent.
        """
        self._validate(voting_result)

        winning_vote = self._resolve_winning_vote(voting_result)
        winning_class = winning_vote.class_name if winning_vote else None
        agreement_ratio = self._calculate_agreement_ratio(voting_result, winning_vote)
        calibrated_confidence = self._calculate_calibrated_confidence(voting_result, winning_vote)
        agreement_statistics = AgreementStatistics.from_voting_result(
            voting_result, agreement_ratio=agreement_ratio
        )

        logger.info(
            "Confidence calibration complete: winning_class=%s calibrated_confidence=%.4f "
            "agreement_ratio=%.4f successful_models=%d failed_models=%d.",
            winning_class,
            calibrated_confidence,
            agreement_ratio,
            len(voting_result.successful_models),
            len(voting_result.failed_models),
        )

        return CalibratedEnsembleResult(
            winning_class=winning_class,
            calibrated_confidence=calibrated_confidence,
            agreement_statistics=agreement_statistics,
            weighted_votes=list(voting_result.weighted_votes),
        )

    @staticmethod
    def _validate(voting_result: VotingResult) -> None:
        """Validate the structural integrity of a supplied `VotingResult`.

        Raises:
            InvalidEnsembleInputError: If `voting_result` is not a
                `VotingResult` instance.
            EnsembleConfigurationError: If `total_models` does not match
                the combined length of `successful_models` and
                `failed_models`.
        """
        if not isinstance(voting_result, VotingResult):
            raise InvalidEnsembleInputError(
                "ConfidenceCalibrationEngine requires a VotingResult instance."
            )

        expected_total = len(voting_result.successful_models) + len(voting_result.failed_models)
        if voting_result.total_models != expected_total:
            raise EnsembleConfigurationError(
                "VotingResult.total_models is inconsistent with its successful/failed "
                "model counts."
            )

    @staticmethod
    def _resolve_winning_vote(voting_result: VotingResult) -> WeightedVote | None:
        """Return the `WeightedVote` with the highest weighted score, if any.

        Ties resolve deterministically to the first maximum encountered in
        `voting_result.weighted_votes`, i.e. the order produced by the
        Adaptive Weighted Voting Engine (ADR-025).

        Args:
            voting_result: The `VotingResult` to inspect.

        Returns:
            The winning `WeightedVote`, or `None` when
            `voting_result.weighted_votes` is empty.
        """
        if not voting_result.weighted_votes:
            return None

        return max(voting_result.weighted_votes, key=lambda vote: vote.weighted_score)

    @staticmethod
    def _calculate_agreement_ratio(
        voting_result: VotingResult, winning_vote: WeightedVote | None
    ) -> float:
        """Calculate the proportion of successful models that agree with the winning class.

        Args:
            voting_result: The `VotingResult` supplying the total count of
                successful models that participated in voting.
            winning_vote: The winning `WeightedVote`, if any.

        Returns:
            `winning_vote.received_votes` divided by the number of
            successful models, clamped to `[0.0, 1.0]` and rounded. `0.0`
            when there is no winning vote or no successful models.
        """
        successful_model_count = len(voting_result.successful_models)
        if winning_vote is None or successful_model_count <= 0:
            return 0.0

        ratio = winning_vote.received_votes / successful_model_count
        return round(min(max(ratio, 0.0), 1.0), _ROUNDING_PRECISION)

    @staticmethod
    def _calculate_calibrated_confidence(
        voting_result: VotingResult, winning_vote: WeightedVote | None
    ) -> float:
        """Calculate the calibrated confidence percentage of the winning class.

        Normalizes the winning class's weighted score against the total
        weighted score accumulated across every candidate class, so the
        result is a stable percentage regardless of how the underlying
        `weighted_score` values are scaled by the voting engine.

        Args:
            voting_result: The `VotingResult` supplying every candidate
                class's weighted score.
            winning_vote: The winning `WeightedVote`, if any.

        Returns:
            The calibrated confidence percentage for `winning_vote`,
            rounded. `0.0` when there is no winning vote or the total
            weighted score across all candidate classes is not positive.
        """
        if winning_vote is None:
            return 0.0

        total_weighted_score = sum(
            vote.weighted_score for vote in voting_result.weighted_votes
        )
        if total_weighted_score <= 0:
            return 0.0

        confidence_percentage = (
            winning_vote.weighted_score / total_weighted_score
        ) * _CONFIDENCE_PERCENTAGE_MULTIPLIER
        return round(confidence_percentage, _ROUNDING_PRECISION)
