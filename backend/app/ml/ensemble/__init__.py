"""Adaptive Ensemble Engine (Phase 3.4, ADR-009), Phase 4.7.1 Adaptive
Ensemble Integration (ADR-024), Phase 4.7.2 Adaptive Weighted Voting
Engine foundation (ADR-025), Phase 4.7.3 Confidence Calibration
(ADR-026), and Phase 4.7.4 Final Prediction Builder foundation (ADR-027).

Combines individual model predictions produced by the Prediction Engine
(Phase 3.3 / ADR-008) into a single, fault-tolerant ensemble prediction
(`AdaptiveEnsembleEngine`), provides the Phase 4.x Prediction API
pipeline's validation/preparation entry point into that same layer
(`EnsembleEngine`, ADR-024), defines the Phase 4.7.2 weighted voting
architecture (`AdaptiveWeightedVotingEngine`, ADR-025), calculates
agreement and calibrated confidence from a `VotingResult`
(`ConfidenceCalibrationEngine`, Phase 4.7.3.2, ADR-026), and builds the
reusable production prediction object from a `CalibratedEnsembleResult`
(`FinalPredictionBuilder`, ADR-027). Contains no FastAPI routing,
database, or TensorFlow concerns.
"""

from app.ml.ensemble.calibration_engine import ConfidenceCalibrationEngine
from app.ml.ensemble.calibration_result import AgreementStatistics, CalibratedEnsembleResult
from app.ml.ensemble.ensemble_engine import AdaptiveEnsembleEngine, EnsembleEngine
from app.ml.ensemble.ensemble_request import EnsembleRequest
from app.ml.ensemble.ensemble_result import EnsembleResult, EnsembleStatus, ValidationSummary
from app.ml.ensemble.exceptions import (
    EnsembleConfigurationError,
    InvalidEnsembleInputError,
    PredictionUnavailableError,
)
from app.ml.ensemble.final_prediction_builder import FinalPredictionBuilder
from app.ml.ensemble.final_prediction_result import FinalPredictionResult
from app.ml.ensemble.response import (
    AgreementLevel,
    AgreementMetrics,
    ConfidenceMetrics,
    EnsemblePredictionResult,
    EnsembleStrategyType,
    ModelContribution,
)
from app.ml.ensemble.voting_engine import AdaptiveWeightedVotingEngine
from app.ml.ensemble.voting_result import VoteScore, VotingResult, WeightedVote

__all__ = [
    "AdaptiveEnsembleEngine",
    "EnsembleEngine",
    "EnsembleRequest",
    "EnsembleResult",
    "EnsembleStatus",
    "ValidationSummary",
    "PredictionUnavailableError",
    "InvalidEnsembleInputError",
    "EnsembleConfigurationError",
    "EnsemblePredictionResult",
    "ModelContribution",
    "ConfidenceMetrics",
    "AgreementMetrics",
    "AgreementLevel",
    "EnsembleStrategyType",
    "AdaptiveWeightedVotingEngine",
    "VotingResult",
    "WeightedVote",
    "VoteScore",
    "ConfidenceCalibrationEngine",
    "CalibratedEnsembleResult",
    "AgreementStatistics",
    "FinalPredictionBuilder",
    "FinalPredictionResult",
]
