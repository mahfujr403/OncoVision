"""Tests for the Phase 4.7.3 Confidence Calibration Engine (ADR-026).

Phase 4.7.3.1 introduced the calibration architecture (validated in
`TestCalibrationResultSchemas` and the structural tests below). Phase
4.7.3.2 -- covered here -- implements the actual agreement-ratio and
calibrated-confidence calculations. Does NOT cover final prediction
selection or response formatting -- those begin in Phase 4.7.4.
"""

import pytest

from app.ml.ensemble.calibration_engine import ConfidenceCalibrationEngine
from app.ml.ensemble.calibration_result import AgreementStatistics, CalibratedEnsembleResult
from app.ml.ensemble.exceptions import EnsembleConfigurationError, InvalidEnsembleInputError
from app.ml.ensemble.voting_result import VotingResult, WeightedVote


@pytest.fixture
def engine() -> ConfidenceCalibrationEngine:
    return ConfidenceCalibrationEngine()


class TestConfidenceCalibrationEngineFoundation:
    """Verifies the calibration architecture introduced by Phase 4.7.3.1."""

    def test_calibrate_accepts_voting_result(self, engine: ConfidenceCalibrationEngine) -> None:
        voting_result = VotingResult.empty()

        result = engine.calibrate(voting_result)

        assert isinstance(result, CalibratedEnsembleResult)

    def test_calibrate_returns_zero_data_result_for_empty_voting_result(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult.empty()

        result = engine.calibrate(voting_result)

        assert result == CalibratedEnsembleResult.empty()
        assert result.winning_class is None
        assert result.calibrated_confidence == 0.0
        assert result.weighted_votes == []
        assert result.agreement_statistics == AgreementStatistics.empty()

    def test_calibrate_rejects_non_voting_result_input(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        with pytest.raises(InvalidEnsembleInputError):
            engine.calibrate(object())  # type: ignore[arg-type]

    def test_calibrate_rejects_inconsistent_total_models(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult(
            weighted_votes=[],
            successful_models=["mobilenet_v2"],
            failed_models=[],
            total_models=5,
            execution_time_ms=0.0,
        )

        with pytest.raises(EnsembleConfigurationError):
            engine.calibrate(voting_result)

    def test_calibrate_carries_weighted_votes_through_unmodified(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        votes = [
            WeightedVote(class_name="lung_n", weighted_score=0.4, received_votes=1),
            WeightedVote(class_name="lung_scc", weighted_score=0.6, received_votes=1),
        ]
        voting_result = VotingResult(
            weighted_votes=votes,
            successful_models=["mobilenet_v2", "densenet_121"],
            failed_models=[],
            total_models=2,
            execution_time_ms=2.1,
        )

        result = engine.calibrate(voting_result)

        assert result.weighted_votes == votes


class TestConfidenceCalibrationEngineCalculation:
    """Verifies the Phase 4.7.3.2 agreement-ratio and confidence calculations."""

    def test_calibrate_identifies_highest_weighted_class(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult(
            weighted_votes=[
                WeightedVote(class_name="lung_n", weighted_score=0.35, received_votes=1),
                WeightedVote(class_name="lung_scc", weighted_score=0.65, received_votes=2),
                WeightedVote(class_name="lung_aca", weighted_score=0.10, received_votes=0),
            ],
            successful_models=["mobilenet_v2", "densenet_121", "efficientnet_resnet_fusion"],
            failed_models=[],
            total_models=3,
            execution_time_ms=3.5,
        )

        result = engine.calibrate(voting_result)

        assert result.winning_class == "lung_scc"

    def test_calibrate_calculates_normalized_calibrated_confidence(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult(
            weighted_votes=[
                WeightedVote(class_name="lung_n", weighted_score=0.30, received_votes=1),
                WeightedVote(class_name="lung_scc", weighted_score=0.90, received_votes=2),
            ],
            successful_models=["mobilenet_v2", "densenet_121"],
            failed_models=[],
            total_models=2,
            execution_time_ms=2.0,
        )

        result = engine.calibrate(voting_result)

        # 0.90 / (0.30 + 0.90) * 100 = 75.0
        assert result.calibrated_confidence == 75.0

    def test_calibrate_calculates_agreement_ratio_from_received_votes(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult(
            weighted_votes=[
                WeightedVote(class_name="lung_n", weighted_score=0.9, received_votes=3),
            ],
            successful_models=["mobilenet_v2", "densenet_121", "efficientnet_resnet_fusion"],
            failed_models=[],
            total_models=3,
            execution_time_ms=4.2,
        )

        result = engine.calibrate(voting_result)

        # 3 agreeing models out of 3 successful models
        assert result.agreement_statistics.agreement_ratio == 1.0

    def test_calibrate_calculates_partial_agreement_ratio(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult(
            weighted_votes=[
                WeightedVote(class_name="lung_n", weighted_score=0.6, received_votes=2),
                WeightedVote(class_name="lung_scc", weighted_score=0.4, received_votes=1),
            ],
            successful_models=["mobilenet_v2", "densenet_121", "efficientnet_resnet_fusion"],
            failed_models=[],
            total_models=3,
            execution_time_ms=4.2,
        )

        result = engine.calibrate(voting_result)

        # winning class "lung_n" received 2 of 3 successful models' votes
        assert result.agreement_statistics.agreement_ratio == round(2 / 3, 4)

    def test_calibrate_is_deterministic_for_the_same_input(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult(
            weighted_votes=[
                WeightedVote(class_name="lung_n", weighted_score=0.55, received_votes=2),
                WeightedVote(class_name="lung_scc", weighted_score=0.45, received_votes=1),
            ],
            successful_models=["mobilenet_v2", "densenet_121", "efficientnet_resnet_fusion"],
            failed_models=[],
            total_models=3,
            execution_time_ms=2.7,
        )

        first = engine.calibrate(voting_result)
        second = ConfidenceCalibrationEngine().calibrate(voting_result)

        assert first == second

    def test_calibrate_handles_zero_total_weighted_score(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult(
            weighted_votes=[
                WeightedVote(class_name="lung_n", weighted_score=0.0, received_votes=0),
            ],
            successful_models=["mobilenet_v2"],
            failed_models=[],
            total_models=1,
            execution_time_ms=1.0,
        )

        result = engine.calibrate(voting_result)

        assert result.winning_class == "lung_n"
        assert result.calibrated_confidence == 0.0

    def test_calibrate_handles_no_successful_models_with_votes(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult(
            weighted_votes=[
                WeightedVote(class_name="lung_n", weighted_score=0.5, received_votes=0),
            ],
            successful_models=[],
            failed_models=["mobilenet_v2"],
            total_models=1,
            execution_time_ms=1.0,
        )

        result = engine.calibrate(voting_result)

        assert result.agreement_statistics.agreement_ratio == 0.0

    def test_calibrate_carries_model_bookkeeping_into_agreement_statistics(
        self, engine: ConfidenceCalibrationEngine
    ) -> None:
        voting_result = VotingResult(
            weighted_votes=[],
            successful_models=["mobilenet_v2"],
            failed_models=["densenet_121"],
            total_models=2,
            execution_time_ms=1.0,
        )

        result = engine.calibrate(voting_result)

        assert result.agreement_statistics.successful_models == ["mobilenet_v2"]
        assert result.agreement_statistics.failed_models == ["densenet_121"]
        assert result.agreement_statistics.total_models == 2
        assert result.agreement_statistics.agreement_ratio == 0.0


class TestCalibrationResultSchemas:
    """Verifies the Phase 4.7.3.1 result schemas hold their expected fields."""

    def test_agreement_statistics_empty_defaults(self) -> None:
        stats = AgreementStatistics.empty()

        assert stats.successful_models == []
        assert stats.failed_models == []
        assert stats.total_models == 0
        assert stats.agreement_ratio == 0.0

    def test_agreement_statistics_from_voting_result_default_ratio(self) -> None:
        voting_result = VotingResult(
            weighted_votes=[],
            successful_models=["mobilenet_v2", "densenet_121"],
            failed_models=["efficientnet_resnet_fusion"],
            total_models=3,
            execution_time_ms=1.5,
        )

        stats = AgreementStatistics.from_voting_result(voting_result)

        assert stats.successful_models == ["mobilenet_v2", "densenet_121"]
        assert stats.failed_models == ["efficientnet_resnet_fusion"]
        assert stats.total_models == 3
        assert stats.agreement_ratio == 0.0

    def test_agreement_statistics_from_voting_result_with_ratio(self) -> None:
        voting_result = VotingResult(
            weighted_votes=[],
            successful_models=["mobilenet_v2"],
            failed_models=[],
            total_models=1,
            execution_time_ms=1.5,
        )

        stats = AgreementStatistics.from_voting_result(voting_result, agreement_ratio=0.5)

        assert stats.agreement_ratio == 0.5

    def test_calibrated_ensemble_result_empty_is_frozen_and_reusable(self) -> None:
        first = CalibratedEnsembleResult.empty()
        second = CalibratedEnsembleResult.empty()

        assert first == second
        with pytest.raises(Exception):
            first.calibrated_confidence = 5.0  # type: ignore[misc]

    def test_calibrated_ensemble_result_holds_expected_fields(self) -> None:
        stats = AgreementStatistics(
            successful_models=["mobilenet_v2"],
            failed_models=[],
            total_models=1,
            agreement_ratio=1.0,
        )
        votes = [WeightedVote(class_name="lung_n", weighted_score=1.0, received_votes=1)]

        result = CalibratedEnsembleResult(
            winning_class="lung_n",
            calibrated_confidence=100.0,
            agreement_statistics=stats,
            weighted_votes=votes,
        )

        assert result.winning_class == "lung_n"
        assert result.calibrated_confidence == 100.0
        assert result.agreement_statistics == stats
        assert result.weighted_votes == votes
