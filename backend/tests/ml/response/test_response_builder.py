"""Tests for the Phase 4.8.1 Response Builder architecture (ADR-028).

Covers only the architecture introduced by this phase: `build` accepts a
`FinalPredictionResult` and copies its predicted class, confidence, and
agreement/model bookkeeping verbatim into a `PredictionResponseResult`.
Does NOT cover API response formatting, PredictionService wiring, router
changes, or runtime statistics attachment -- those begin in Phase 4.8.2
onward.
"""

import pytest

from app.ml.ensemble.final_prediction_result import FinalPredictionResult
from app.ml.response.exceptions import InvalidResponseInputError
from app.ml.response.response_builder import PredictionResponseBuilder
from app.ml.response.response_result import PredictionResponseResult


@pytest.fixture
def builder() -> PredictionResponseBuilder:
    return PredictionResponseBuilder()


class TestPredictionResponseBuilderArchitecture:
    """Verifies Phase 4.8.1 introduces only the Response Builder architecture."""

    def test_build_accepts_final_prediction_result(
        self, builder: PredictionResponseBuilder
    ) -> None:
        final_result = FinalPredictionResult.empty()

        result = builder.build(final_result)

        assert isinstance(result, PredictionResponseResult)

    def test_build_returns_zero_data_result_for_empty_final_result(
        self, builder: PredictionResponseBuilder
    ) -> None:
        final_result = FinalPredictionResult.empty()

        result = builder.build(final_result)

        assert result == PredictionResponseResult.empty()
        assert result.predicted_class is None
        assert result.confidence == 0.0
        assert result.agreement_ratio == 0.0
        assert result.successful_models == []
        assert result.failed_models == []
        assert result.participating_models == 0

    def test_build_copies_predicted_class_unchanged(
        self, builder: PredictionResponseBuilder
    ) -> None:
        final_result = FinalPredictionResult(
            predicted_class="lung_scc",
            confidence=82.5,
            agreement_ratio=1.0,
            successful_models=["mobilenet_v2", "densenet_121"],
            failed_models=[],
            participating_models=2,
        )

        result = builder.build(final_result)

        assert result.predicted_class == "lung_scc"

    def test_build_copies_confidence_unchanged(self, builder: PredictionResponseBuilder) -> None:
        final_result = FinalPredictionResult(
            predicted_class="lung_n",
            confidence=73.4567,
            agreement_ratio=0.0,
            successful_models=[],
            failed_models=[],
            participating_models=0,
        )

        result = builder.build(final_result)

        assert result.confidence == 73.4567

    def test_build_copies_agreement_and_model_bookkeeping(
        self, builder: PredictionResponseBuilder
    ) -> None:
        final_result = FinalPredictionResult(
            predicted_class="lung_aca",
            confidence=60.0,
            agreement_ratio=0.6667,
            successful_models=["mobilenet_v2", "densenet_121"],
            failed_models=["efficientnet_resnet_fusion"],
            participating_models=3,
        )

        result = builder.build(final_result)

        assert result.agreement_ratio == 0.6667
        assert result.successful_models == ["mobilenet_v2", "densenet_121"]
        assert result.failed_models == ["efficientnet_resnet_fusion"]
        assert result.participating_models == 3

    def test_build_does_not_modify_the_source_final_prediction_result(
        self, builder: PredictionResponseBuilder
    ) -> None:
        final_result = FinalPredictionResult(
            predicted_class="lung_n",
            confidence=55.5,
            agreement_ratio=1.0,
            successful_models=["mobilenet_v2"],
            failed_models=[],
            participating_models=1,
        )

        builder.build(final_result)

        # FinalPredictionResult remains untouched -- verifies the Response
        # Builder never mutates or recalculates its upstream input.
        assert final_result.predicted_class == "lung_n"
        assert final_result.confidence == 55.5
        assert final_result.agreement_ratio == 1.0
        assert final_result.successful_models == ["mobilenet_v2"]
        assert final_result.participating_models == 1

    def test_build_is_deterministic_for_the_same_input(
        self, builder: PredictionResponseBuilder
    ) -> None:
        final_result = FinalPredictionResult(
            predicted_class="lung_scc",
            confidence=91.2,
            agreement_ratio=1.0,
            successful_models=["mobilenet_v2", "densenet_121"],
            failed_models=[],
            participating_models=2,
        )

        first = builder.build(final_result)
        second = PredictionResponseBuilder().build(final_result)

        assert first == second

    def test_build_rejects_non_final_prediction_result_input(
        self, builder: PredictionResponseBuilder
    ) -> None:
        with pytest.raises(InvalidResponseInputError):
            builder.build(object())  # type: ignore[arg-type]


class TestPredictionResponseResultSchema:
    """Verifies the Phase 4.8.1 result schema holds its expected fields."""

    def test_prediction_response_result_empty_defaults(self) -> None:
        result = PredictionResponseResult.empty()

        assert result.predicted_class is None
        assert result.confidence == 0.0
        assert result.agreement_ratio == 0.0
        assert result.successful_models == []
        assert result.failed_models == []
        assert result.participating_models == 0

    def test_prediction_response_result_is_frozen(self) -> None:
        result = PredictionResponseResult.empty()

        with pytest.raises(Exception):
            result.confidence = 10.0  # type: ignore[misc]

    def test_prediction_response_result_holds_expected_fields(self) -> None:
        result = PredictionResponseResult(
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
