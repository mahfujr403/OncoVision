"""Shared test helpers for the Phase 5.1 Prediction History test suite.

Builds minimal `PredictionContext` and `PredictionResult` instances
without depending on the full upload/runtime/prediction pipeline, so
these tests exercise only the `app.history` package's own mapping logic
(ADR-032).
"""

from app.ml.prediction.prediction_result import ConfidenceResult, IndividualPrediction
from app.ml.response.response_result import PredictionResponseResult
from app.services.prediction_context import PredictionContext, PredictionOptions
from app.services.prediction_result import (
    PipelineStageName,
    PipelineStageRecord,
    PipelineStageStatus,
    PredictionResult,
)


def make_options(**overrides) -> PredictionOptions:
    defaults = dict(
        confidence_threshold=50.0,
        include_individual_predictions=True,
        include_runtime_statistics=True,
        save_history=True,
        generate_report=False,
    )
    defaults.update(overrides)
    return PredictionOptions(**defaults)


def make_context(**overrides) -> PredictionContext:
    defaults = dict(
        request_id="req-0001",
        requested_at="2026-07-27T10:00:00+00:00",
        user_id="user-0001",
        user_email="pathologist@example.com",
        image_filename="sample.png",
        image_content_type="image/png",
        image_size_bytes=204800,
        image_width=224,
        image_height=224,
        options=make_options(),
    )
    defaults.update(overrides)
    return PredictionContext(**defaults)


def make_stage_record(
    name: PipelineStageName, status: PipelineStageStatus = PipelineStageStatus.COMPLETED
) -> PipelineStageRecord:
    return PipelineStageRecord(name=name, status=status, detail="test stage")


def make_individual_prediction(
    model_name: str = "MobileNetV2",
    predicted_label: str = "lung_aca",
    confidence_percentage: float = 91.2,
    inference_time_ms: float = 42.0,
) -> IndividualPrediction:
    return IndividualPrediction(
        model_id=model_name.lower(),
        model_name=model_name,
        model_version="1.0.0",
        predicted_label=predicted_label,
        predicted_class_index=0,
        confidence=ConfidenceResult(
            raw_probabilities=[confidence_percentage / 100.0, 1 - confidence_percentage / 100.0],
            confidence_percentage=confidence_percentage,
            top_class=predicted_label,
            top_class_index=0,
            top_k_predictions=[],
        ),
        inference_time_ms=inference_time_ms,
    )


def make_response_result(**overrides) -> PredictionResponseResult:
    defaults = dict(
        predicted_class="lung_aca",
        confidence=91.2,
        agreement_ratio=1.0,
        successful_models=["mobilenetv2"],
        failed_models=[],
        participating_models=1,
    )
    defaults.update(overrides)
    return PredictionResponseResult(**defaults)


def make_prediction_result(**overrides) -> PredictionResult:
    defaults = dict(
        request_id="req-0001",
        requested_at="2026-07-27T10:00:00+00:00",
        message="Prediction completed successfully.",
        stages=[
            make_stage_record(PipelineStageName.PREDICTION_ENGINE),
            make_stage_record(PipelineStageName.RESPONSE),
        ],
    )
    defaults.update(overrides)
    return PredictionResult(**defaults)
