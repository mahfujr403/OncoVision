"""Tests for the Phase 5.1 Prediction History Mapper architecture (ADR-032).

Covers only the mapping architecture introduced by this phase: building
an immutable `PredictionHistory` from an already-completed
`PredictionResult`/`PredictionContext` pair. Does NOT cover persistence,
retrieval, pagination, or PredictionService/router wiring -- those begin
in Phase 5.2 onward.
"""

import pytest

from app.history.enums import PredictionHistoryStatus
from app.history.exceptions import InvalidHistoryInputError
from app.history.mapper import PredictionHistoryMapper
from app.history.prediction_history import PredictionHistory
from tests.history.conftest_helpers import (
    make_context,
    make_individual_prediction,
    make_prediction_result,
    make_response_result,
)


@pytest.fixture
def mapper() -> PredictionHistoryMapper:
    return PredictionHistoryMapper()


class TestPredictionHistoryMapperArchitecture:
    """Verifies Phase 5.1 introduces only the Prediction History mapping architecture."""

    def test_to_history_returns_prediction_history(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context()
        prediction_result = make_prediction_result(
            response_result=make_response_result(),
            individual_model_results=[make_individual_prediction()],
        )

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert isinstance(history, PredictionHistory)

    def test_to_history_copies_request_and_user_identifiers(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context(request_id="req-9999", user_id="user-9999")
        prediction_result = make_prediction_result(
            request_id="req-9999",
            response_result=make_response_result(),
        )

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert history.request_id == "req-9999"
        assert history.user_id == "user-9999"
        assert history.metadata.user_id == "user-9999"

    def test_to_history_generates_a_history_id_distinct_from_request_id(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context(request_id="req-0001")
        prediction_result = make_prediction_result(
            request_id="req-0001", response_result=make_response_result()
        )

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert history.history_id
        assert history.history_id != history.request_id

    def test_to_history_copies_image_and_request_metadata_from_context(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context(
            image_filename="biopsy.tiff",
            image_content_type="image/tiff",
            image_size_bytes=512000,
            image_width=512,
            image_height=512,
        )
        prediction_result = make_prediction_result(response_result=make_response_result())

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert history.metadata.image_filename == "biopsy.tiff"
        assert history.metadata.image_content_type == "image/tiff"
        assert history.metadata.image_size_bytes == 512000
        assert history.metadata.image_width == 512
        assert history.metadata.image_height == 512

    def test_to_history_status_is_pending_when_response_stage_did_not_complete(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context()
        prediction_result = make_prediction_result(response_result=None)

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert history.status == PredictionHistoryStatus.PENDING
        assert history.summary.predicted_class is None
        assert history.summary.participating_models == 0

    def test_to_history_status_is_success_with_no_failed_models(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context()
        prediction_result = make_prediction_result(
            response_result=make_response_result(failed_models=[], successful_models=["mobilenetv2"])
        )

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert history.status == PredictionHistoryStatus.SUCCESS

    def test_to_history_status_is_partial_success_with_failed_models(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context()
        prediction_result = make_prediction_result(
            response_result=make_response_result(
                successful_models=["mobilenetv2"],
                failed_models=["densenet121"],
                participating_models=2,
            )
        )

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert history.status == PredictionHistoryStatus.PARTIAL_SUCCESS

    def test_to_history_status_is_failed_with_no_predicted_class(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context()
        prediction_result = make_prediction_result(
            response_result=make_response_result(
                predicted_class=None,
                successful_models=[],
                failed_models=["mobilenetv2"],
                participating_models=1,
            )
        )

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert history.status == PredictionHistoryStatus.FAILED

    def test_to_history_copies_ensemble_summary_verbatim(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context()
        response_result = make_response_result(
            predicted_class="lung_scc",
            confidence=88.4,
            agreement_ratio=0.75,
            successful_models=["mobilenetv2", "densenet121"],
            failed_models=["efficientnet_resnet_fusion"],
            participating_models=3,
        )
        prediction_result = make_prediction_result(response_result=response_result)

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert history.summary.predicted_class == "lung_scc"
        assert history.summary.confidence == 88.4
        assert history.summary.agreement_ratio == 0.75
        assert history.summary.successful_models == ["mobilenetv2", "densenet121"]
        assert history.summary.failed_models == ["efficientnet_resnet_fusion"]
        assert history.summary.participating_models == 3

    def test_to_history_copies_individual_model_breakdown(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context()
        individual = make_individual_prediction(
            model_name="MobileNetV2",
            predicted_label="lung_aca",
            confidence_percentage=93.5,
            inference_time_ms=41.2,
        )
        prediction_result = make_prediction_result(
            response_result=make_response_result(),
            individual_model_results=[individual],
        )

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        assert len(history.summary.individual_predictions) == 1
        entry = history.summary.individual_predictions[0]
        assert entry.model_name == "MobileNetV2"
        assert entry.prediction == "lung_aca"
        assert entry.confidence == 93.5
        assert entry.inference_time_ms == 41.2

    def test_to_history_does_not_modify_the_source_prediction_result(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        context = make_context()
        response_result = make_response_result(predicted_class="lung_n", confidence=55.5)
        prediction_result = make_prediction_result(response_result=response_result)

        mapper.to_history(prediction_result=prediction_result, context=context)

        # PredictionResult and its nested response_result remain untouched --
        # verifies the mapper never mutates or recalculates its upstream input.
        assert prediction_result.response_result.predicted_class == "lung_n"
        assert prediction_result.response_result.confidence == 55.5

    def test_to_history_result_is_frozen(self, mapper: PredictionHistoryMapper) -> None:
        context = make_context()
        prediction_result = make_prediction_result(response_result=make_response_result())

        history = mapper.to_history(prediction_result=prediction_result, context=context)

        with pytest.raises(Exception):
            history.request_id = "mutated"  # type: ignore[misc]

    def test_to_history_rejects_non_prediction_result_input(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        with pytest.raises(InvalidHistoryInputError):
            mapper.to_history(prediction_result=object(), context=make_context())  # type: ignore[arg-type]

    def test_to_history_rejects_non_prediction_context_input(
        self, mapper: PredictionHistoryMapper
    ) -> None:
        with pytest.raises(InvalidHistoryInputError):
            mapper.to_history(
                prediction_result=make_prediction_result(response_result=make_response_result()),
                context=object(),  # type: ignore[arg-type]
            )


class TestPredictionHistoryDomainModel:
    """Verifies the Phase 5.1 domain model holds its expected shape."""

    def test_prediction_history_empty_factory_defaults(self) -> None:
        context = make_context()
        from app.history.metadata import PredictionHistoryMetadata

        metadata = PredictionHistoryMetadata(
            request_id=context.request_id,
            requested_at=context.requested_at,
            user_id=context.user_id,
            user_email=context.user_email,
            image_filename=context.image_filename,
            image_content_type=context.image_content_type,
            image_size_bytes=context.image_size_bytes,
            image_width=context.image_width,
            image_height=context.image_height,
        )

        history = PredictionHistory.empty(
            history_id="hist-0001",
            request_id="req-0001",
            user_id="user-0001",
            created_at="2026-07-27T10:00:00+00:00",
            metadata=metadata,
        )

        assert history.status == PredictionHistoryStatus.PENDING
        assert history.summary.predicted_class is None
        assert history.summary.participating_models == 0
