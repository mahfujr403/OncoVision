"""Tests for the Phase 4.7.4 Final Prediction Builder foundation (ADR-027).

Covers only the architecture introduced by this phase: `build` accepts a
`CalibratedEnsembleResult` and copies its winning class, calibrated
confidence, and agreement statistics verbatim into a
`FinalPredictionResult`. Does NOT cover response formatting -- that
begins in Phase 4.8.
"""

import pytest

from app.ml.ensemble.calibration_result import AgreementStatistics, CalibratedEnsembleResult
from app.ml.ensemble.exceptions import InvalidEnsembleInputError
from app.ml.ensemble.final_prediction_builder import FinalPredictionBuilder
from app.ml.ensemble.final_prediction_result import FinalPredictionResult
from app.ml.ensemble.voting_result import WeightedVote


@pytest.fixture
def builder() -> FinalPredictionBuilder:
    return FinalPredictionBuilder()


class TestFinalPredictionBuilderFoundation:
    """Verifies Phase 4.7.4 introduces only the final prediction architecture."""

    def test_build_accepts_calibrated_ensemble_result(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = CalibratedEnsembleResult.empty()

        result = builder.build(calibrated_result)

        assert isinstance(result, FinalPredictionResult)

    def test_build_returns_zero_data_result_for_empty_calibrated_result(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = CalibratedEnsembleResult.empty()

        result = builder.build(calibrated_result)

        assert result == FinalPredictionResult.empty()
        assert result.predicted_class is None
        assert result.confidence == 0.0
        assert result.agreement_ratio == 0.0
        assert result.successful_models == []
        assert result.failed_models == []
        assert result.participating_models == 0

    def test_build_copies_winning_class_as_predicted_class(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = CalibratedEnsembleResult(
            winning_class="lung_scc",
            calibrated_confidence=82.5,
            agreement_statistics=AgreementStatistics(
                successful_models=["mobilenet_v2", "densenet_121"],
                failed_models=[],
                total_models=2,
                agreement_ratio=1.0,
            ),
            weighted_votes=[
                WeightedVote(class_name="lung_scc", weighted_score=0.9, received_votes=2),
            ],
        )

        result = builder.build(calibrated_result)

        assert result.predicted_class == "lung_scc"

    def test_build_copies_calibrated_confidence_unchanged(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = CalibratedEnsembleResult(
            winning_class="lung_n",
            calibrated_confidence=73.4567,
            agreement_statistics=AgreementStatistics.empty(),
            weighted_votes=[],
        )

        result = builder.build(calibrated_result)

        assert result.confidence == 73.4567

    def test_build_copies_agreement_statistics(self, builder: FinalPredictionBuilder) -> None:
        calibrated_result = CalibratedEnsembleResult(
            winning_class="lung_aca",
            calibrated_confidence=60.0,
            agreement_statistics=AgreementStatistics(
                successful_models=["mobilenet_v2", "densenet_121"],
                failed_models=["efficientnet_resnet_fusion"],
                total_models=3,
                agreement_ratio=0.6667,
            ),
            weighted_votes=[],
        )

        result = builder.build(calibrated_result)

        assert result.agreement_ratio == 0.6667
        assert result.successful_models == ["mobilenet_v2", "densenet_121"]
        assert result.failed_models == ["efficientnet_resnet_fusion"]
        assert result.participating_models == 3

    def test_build_does_not_modify_weighted_votes_or_recompute_anything(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = CalibratedEnsembleResult(
            winning_class="lung_n",
            calibrated_confidence=55.5,
            agreement_statistics=AgreementStatistics(
                successful_models=["mobilenet_v2"],
                failed_models=[],
                total_models=1,
                agreement_ratio=1.0,
            ),
            weighted_votes=[
                WeightedVote(class_name="lung_n", weighted_score=0.5, received_votes=1),
                WeightedVote(class_name="lung_scc", weighted_score=0.3, received_votes=0),
            ],
        )

        result = builder.build(calibrated_result)

        # FinalPredictionResult carries no weighted_votes field -- verifies the
        # source CalibratedEnsembleResult itself remains untouched.
        assert calibrated_result.weighted_votes[0].weighted_score == 0.5
        assert calibrated_result.weighted_votes[1].weighted_score == 0.3
        assert result.confidence == 55.5

    def test_build_is_deterministic_for_the_same_input(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = CalibratedEnsembleResult(
            winning_class="lung_scc",
            calibrated_confidence=91.2,
            agreement_statistics=AgreementStatistics(
                successful_models=["mobilenet_v2", "densenet_121"],
                failed_models=[],
                total_models=2,
                agreement_ratio=1.0,
            ),
            weighted_votes=[],
        )

        first = builder.build(calibrated_result)
        second = FinalPredictionBuilder().build(calibrated_result)

        assert first == second

    def test_build_rejects_non_calibrated_ensemble_result_input(
        self, builder: FinalPredictionBuilder
    ) -> None:
        with pytest.raises(InvalidEnsembleInputError):
            builder.build(object())  # type: ignore[arg-type]


class TestFinalPredictionResultSchema:
    """Verifies the Phase 4.7.4 result schema holds its expected fields."""

    def test_final_prediction_result_empty_defaults(self) -> None:
        result = FinalPredictionResult.empty()

        assert result.predicted_class is None
        assert result.confidence == 0.0
        assert result.agreement_ratio == 0.0
        assert result.successful_models == []
        assert result.failed_models == []
        assert result.participating_models == 0

    def test_final_prediction_result_is_frozen(self) -> None:
        result = FinalPredictionResult.empty()

        with pytest.raises(Exception):
            result.confidence = 10.0  # type: ignore[misc]

    def test_final_prediction_result_holds_expected_fields(self) -> None:
        result = FinalPredictionResult(
            predicted_class="lung_n",
            confidence=88.8,
            agreement_ratio=1.0,
            successful_models=["mobilenet_v2"],
            failed_models=[],
            participating_models=1,
        )

        assert result.predicted_class == "lung_n"
        assert result.confidence == 88.8
        assert result.agreement_ratio == 1.0
        assert result.successful_models == ["mobilenet_v2"]
        assert result.failed_models == []
        assert result.participating_models == 1
