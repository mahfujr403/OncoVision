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
from app.ml.prediction.prediction_result import ConfidenceResult, IndividualPrediction, TopClassPrediction


def _individual_prediction(
    model_id: str, predicted_label: str, confidence_percentage: float
) -> IndividualPrediction:
    """Build a minimal `IndividualPrediction` with a given top-class confidence."""
    confidence = ConfidenceResult(
        raw_probabilities=[confidence_percentage / 100],
        confidence_percentage=confidence_percentage,
        top_class=predicted_label,
        top_class_index=0,
        top_k_predictions=[
            TopClassPrediction(
                label=predicted_label, class_index=0, confidence_percentage=confidence_percentage
            )
        ],
    )
    return IndividualPrediction(
        model_id=model_id,
        model_name=model_id.replace("_", " ").title(),
        model_version="1.0.0",
        predicted_label=predicted_label,
        predicted_class_index=0,
        confidence=confidence,
        inference_time_ms=10.0,
    )


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


class TestUnknownInputGuard:
    """Verifies the unknown-input guard described in the Phase 4.7.4 update.

    Reported predicted class becomes "unknown" whenever either:
        - the calibrated combined confidence is below 92%, or
        - any individual model's own top-class confidence is below 80%,
    but only when `individual_predictions` is supplied to `build()`.
    """

    @staticmethod
    def _calibrated_result(winning_class: str = "lung_aca", calibrated_confidence: float = 95.0):
        return CalibratedEnsembleResult(
            winning_class=winning_class,
            calibrated_confidence=calibrated_confidence,
            agreement_statistics=AgreementStatistics(
                successful_models=["mobilenet_v2", "densenet_121"],
                failed_models=[],
                total_models=2,
                agreement_ratio=1.0,
            ),
            weighted_votes=[
                WeightedVote(class_name=winning_class, weighted_score=0.95, received_votes=2),
            ],
        )

    def test_guard_is_skipped_when_individual_predictions_not_supplied(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = self._calibrated_result(calibrated_confidence=50.0)

        result = builder.build(calibrated_result)

        assert result.predicted_class == "lung_aca"

    def test_high_confidence_prediction_is_reported_normally(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = self._calibrated_result(calibrated_confidence=95.0)
        individual_predictions = [
            _individual_prediction("mobilenet_v2", "lung_aca", 96.0),
            _individual_prediction("densenet_121", "lung_aca", 94.0),
        ]

        result = builder.build(calibrated_result, individual_predictions=individual_predictions)

        assert result.predicted_class == "lung_aca"

    def test_combined_confidence_below_threshold_becomes_unknown(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = self._calibrated_result(calibrated_confidence=91.9)
        individual_predictions = [
            _individual_prediction("mobilenet_v2", "lung_aca", 92.0),
            _individual_prediction("densenet_121", "lung_aca", 92.0),
        ]

        result = builder.build(calibrated_result, individual_predictions=individual_predictions)

        assert result.predicted_class == "unknown"

    def test_combined_confidence_at_threshold_is_not_unknown(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = self._calibrated_result(calibrated_confidence=92.0)
        individual_predictions = [
            _individual_prediction("mobilenet_v2", "lung_aca", 92.0),
            _individual_prediction("densenet_121", "lung_aca", 92.0),
        ]

        result = builder.build(calibrated_result, individual_predictions=individual_predictions)

        assert result.predicted_class == "lung_aca"

    def test_single_low_confidence_model_becomes_unknown_even_with_high_combined_confidence(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = self._calibrated_result(calibrated_confidence=97.0)
        individual_predictions = [
            _individual_prediction("mobilenet_v2", "lung_aca", 99.0),
            _individual_prediction("densenet_121", "lung_aca", 79.9),
        ]

        result = builder.build(calibrated_result, individual_predictions=individual_predictions)

        assert result.predicted_class == "unknown"

    def test_individual_confidence_at_threshold_is_not_unknown(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = self._calibrated_result(calibrated_confidence=97.0)
        individual_predictions = [
            _individual_prediction("mobilenet_v2", "lung_aca", 99.0),
            _individual_prediction("densenet_121", "lung_aca", 80.0),
        ]

        result = builder.build(calibrated_result, individual_predictions=individual_predictions)

        assert result.predicted_class == "lung_aca"

    def test_both_conditions_failing_still_becomes_unknown(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = self._calibrated_result(calibrated_confidence=60.0)
        individual_predictions = [
            _individual_prediction("mobilenet_v2", "lung_aca", 55.0),
            _individual_prediction("densenet_121", "lung_aca", 65.0),
        ]

        result = builder.build(calibrated_result, individual_predictions=individual_predictions)

        assert result.predicted_class == "unknown"

    def test_guard_does_not_apply_when_there_is_no_winning_class(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = CalibratedEnsembleResult.empty()
        individual_predictions = [_individual_prediction("mobilenet_v2", "lung_aca", 10.0)]

        result = builder.build(calibrated_result, individual_predictions=individual_predictions)

        assert result.predicted_class is None

    def test_guard_is_skipped_for_an_empty_individual_predictions_list(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = self._calibrated_result(calibrated_confidence=10.0)

        result = builder.build(calibrated_result, individual_predictions=[])

        assert result.predicted_class == "lung_aca"

    def test_unknown_prediction_still_carries_original_confidence_and_agreement(
        self, builder: FinalPredictionBuilder
    ) -> None:
        calibrated_result = self._calibrated_result(calibrated_confidence=60.0)
        individual_predictions = [
            _individual_prediction("mobilenet_v2", "lung_aca", 55.0),
            _individual_prediction("densenet_121", "lung_aca", 65.0),
        ]

        result = builder.build(calibrated_result, individual_predictions=individual_predictions)

        assert result.predicted_class == "unknown"
        assert result.confidence == 60.0
        assert result.agreement_ratio == 1.0
        assert result.successful_models == ["mobilenet_v2", "densenet_121"]
        assert result.participating_models == 2


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
