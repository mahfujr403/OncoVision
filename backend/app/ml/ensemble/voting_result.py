"""Voting Result (Phase 4.7.2 - Adaptive Weighted Voting Engine, ADR-025).

`VotingResult` is the standardized, fully-serializable output of the
`AdaptiveWeightedVotingEngine` (`app.ml.ensemble.voting_engine`).

Per ADR-025, this phase only defines the voting architecture. No weighted
scores are calculated yet -- `AdaptiveWeightedVotingEngine.calculate_votes`
currently always returns an empty `VotingResult` (`VotingResult.empty`).
Vote-score calculation, confidence calibration, and final prediction
selection are introduced by later phases:
    - Phase 4.7.2: Adaptive Weighted Voting (this phase, foundation only)
    - Phase 4.7.3: Confidence Calibration
    - Phase 4.7.4: Final Prediction Builder
"""

from pydantic import BaseModel, ConfigDict, Field


class VoteScore(BaseModel):
    """A single model's weighted contribution toward its predicted class.

    Reused, per-model input to weighted voting -- never redefines
    information already produced by the Prediction Engine (ADR-008); it
    only carries the subset of that information, plus the model's
    manifest-configured `ensemble_weight` (ADR-006), that voting requires.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(description="Unique identifier of the model that produced this vote.")
    model_name: str = Field(description="Human-readable display name of the model.")
    ensemble_weight: float = Field(
        description="Manifest-configured `ensemble_weight` for this model (ADR-006)."
    )
    predicted_label: str = Field(description="This model's own individual predicted class label.")
    confidence: float = Field(
        description="This model's own individual top-class confidence percentage."
    )


class WeightedVote(BaseModel):
    """Aggregated weighted-voting outcome for a single candidate class label.

    One `WeightedVote` per distinct class label that received at least one
    model's vote, once voting is implemented (Phase 4.7.2 onward).
    """

    model_config = ConfigDict(frozen=True)

    class_name: str = Field(description="Candidate class label this weighted vote describes.")
    weighted_score: float = Field(
        description="Combined, manifest-weighted vote score accumulated for this class label."
    )
    received_votes: int = Field(
        description="Number of executed models whose own prediction selected this class label."
    )


class VotingResult(BaseModel):
    """Standardized output of the Phase 4.7.2 Adaptive Weighted Voting Engine.

    Constructed exactly once per prediction request by
    `AdaptiveWeightedVotingEngine`. In this phase, always the empty result
    produced by `VotingResult.empty` -- carries NO weighted vote scores,
    NO confidence calibration, and NO final prediction selection.
    """

    model_config = ConfigDict(frozen=True)

    weighted_votes: list[WeightedVote] = Field(
        default_factory=list,
        description=(
            "Aggregated weighted-voting outcome per candidate class label. "
            "Always empty in this phase (ADR-025)."
        ),
    )
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
    execution_time_ms: float = Field(
        default=0.0,
        description="Time spent inside the voting engine for this request, in milliseconds.",
    )

    @classmethod
    def empty(cls) -> "VotingResult":
        """Return the empty `VotingResult` produced by this phase (ADR-025).

        The single, reusable construction point for the placeholder result
        `AdaptiveWeightedVotingEngine.calculate_votes` returns until Phase
        4.7.2 voting logic is implemented.
        """
        return cls(
            weighted_votes=[],
            successful_models=[],
            failed_models=[],
            total_models=0,
            execution_time_ms=0.0,
        )
