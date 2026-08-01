"""Calibrated Ensemble Result (Phase 4.7.3 - Confidence Calibration, ADR-026).

`CalibratedEnsembleResult` is the standardized, fully-serializable output of
the `ConfidenceCalibrationEngine` (`app.ml.ensemble.calibration_engine`).

Per the ADR-026 Update, Phase 4.7.3 is implemented in two steps:
    - Phase 4.7.3.1: Calibration architecture (`CalibratedEnsembleResult`,
      `AgreementStatistics`, validation).
    - Phase 4.7.3.2: Agreement & confidence calculation (this step) --
      `winning_class`, `calibrated_confidence`, and
      `AgreementStatistics.agreement_ratio` are now fully calculated from
      `VotingResult` by `ConfidenceCalibrationEngine`.

Final prediction selection remains out of scope for Phase 4.7.3 and is
introduced by a later phase:
    - Phase 4.7.2: Adaptive Weighted Voting (completed)
    - Phase 4.7.3: Confidence Calibration (this phase, complete)
    - Phase 4.7.4: Final Prediction Builder
"""

from pydantic import BaseModel, ConfigDict, Field

from app.ml.ensemble.voting_result import VotingResult, WeightedVote


class AgreementStatistics(BaseModel):
    """Reusable breakdown of model participation for a calibrated ensemble result.

    Carries the same successful/failed/total model bookkeeping already
    produced by `VotingResult` (ADR-025), plus `agreement_ratio` -- the
    proportion of successful models that agree with the winning class,
    calculated by `ConfidenceCalibrationEngine` (Phase 4.7.3.2, ADR-026).
    """

    model_config = ConfigDict(frozen=True)

    successful_models: list[str] = Field(
        default_factory=list,
        description="Model IDs whose predictions participated in voting, in execution order.",
    )
    failed_models: list[str] = Field(
        default_factory=list,
        description="Model IDs that were attempted but failed to produce a prediction.",
    )
    total_models: int = Field(
        default=0,
        description="Total number of models attempted (successful and failed) for this request.",
    )
    agreement_ratio: float = Field(
        default=0.0,
        description=(
            "Proportion of successful models whose own individual prediction agrees "
            "with the winning class, in the range [0.0, 1.0]. Calculated by "
            "`ConfidenceCalibrationEngine` from the winning `WeightedVote`'s "
            "`received_votes` (Phase 4.7.3.2, ADR-026)."
        ),
    )

    @classmethod
    def empty(cls) -> "AgreementStatistics":
        """Return an `AgreementStatistics` with no models and zero agreement."""
        return cls(successful_models=[], failed_models=[], total_models=0, agreement_ratio=0.0)

    @classmethod
    def from_voting_result(
        cls, voting_result: VotingResult, agreement_ratio: float = 0.0
    ) -> "AgreementStatistics":
        """Build an `AgreementStatistics` from a `VotingResult`'s model participation.

        Args:
            voting_result: The `VotingResult` supplied to the Confidence
                Calibration Engine for this request.
            agreement_ratio: The proportion of successful models that
                agree with the winning class, as calculated by
                `ConfidenceCalibrationEngine` (Phase 4.7.3.2, ADR-026).
                Defaults to `0.0` for callers that have not yet
                calculated it.

        Returns:
            An `AgreementStatistics` reflecting `voting_result`'s model
            participation, with `agreement_ratio` set to the supplied
            value.
        """
        return cls(
            successful_models=list(voting_result.successful_models),
            failed_models=list(voting_result.failed_models),
            total_models=voting_result.total_models,
            agreement_ratio=agreement_ratio,
        )


class CalibratedEnsembleResult(BaseModel):
    """Standardized output of the Phase 4.7.3 Confidence Calibration Engine.

    Constructed exactly once per prediction request by
    `ConfidenceCalibrationEngine`. `winning_class` reflects the highest
    weighted class found in `VotingResult.weighted_votes` (or `None` when
    no weighted votes are present); `calibrated_confidence` and
    `agreement_statistics.agreement_ratio` are fully calculated from that
    same `VotingResult` (Phase 4.7.3.2, ADR-026). Final prediction
    selection and response formatting remain out of scope -- introduced by
    the future Final Prediction Builder (Phase 4.7.4).
    """

    model_config = ConfigDict(frozen=True)

    winning_class: str | None = Field(
        default=None,
        description=(
            "Candidate class label with the highest weighted vote score in the "
            "supplied VotingResult. None when no weighted votes are present yet."
        ),
    )
    calibrated_confidence: float = Field(
        default=0.0,
        description=(
            "Calibrated ensemble confidence percentage for `winning_class`, calculated "
            "as its weighted score normalized against the total weighted score across "
            "every candidate class (Phase 4.7.3.2, ADR-026)."
        ),
    )
    agreement_statistics: AgreementStatistics = Field(
        default_factory=AgreementStatistics.empty,
        description="Model participation and agreement breakdown for this result.",
    )
    weighted_votes: list[WeightedVote] = Field(
        default_factory=list,
        description=(
            "Weighted votes carried through unmodified from the supplied VotingResult. "
            "Never recalculated by the Confidence Calibration Engine."
        ),
    )

    @classmethod
    def empty(cls) -> "CalibratedEnsembleResult":
        """Return the zero-data `CalibratedEnsembleResult`.

        This is the mathematically correct output `ConfidenceCalibrationEngine`
        produces for a `VotingResult` with no weighted votes -- for example,
        the empty result currently returned by
        `AdaptiveWeightedVotingEngine.calculate_votes` (ADR-025).
        """
        return cls(
            winning_class=None,
            calibrated_confidence=0.0,
            agreement_statistics=AgreementStatistics.empty(),
            weighted_votes=[],
        )
