"""Shared test helpers for the Phase 6.1 Reporting test suite.

Builds minimal `PredictionHistory` instances without depending on the
full prediction pipeline, so these tests exercise only the
`app.reports` package's own aggregation logic (ADR-037).
"""

from app.history.enums import PredictionHistoryStatus
from app.history.metadata import PredictionHistoryMetadata
from app.history.prediction_history import PredictionHistory
from app.history.summary import PredictionHistoryModelEntry, PredictionHistorySummary


def make_metadata(**overrides) -> PredictionHistoryMetadata:
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
    )
    defaults.update(overrides)
    return PredictionHistoryMetadata(**defaults)


def make_summary(**overrides) -> PredictionHistorySummary:
    defaults = dict(
        predicted_class="lung_aca",
        confidence=91.2,
        agreement_ratio=1.0,
        successful_models=["mobilenetv2"],
        failed_models=[],
        participating_models=1,
        individual_predictions=[
            PredictionHistoryModelEntry(
                model_name="MobileNetV2",
                prediction="lung_aca",
                confidence=91.2,
                inference_time_ms=42.0,
            )
        ],
    )
    defaults.update(overrides)
    return PredictionHistorySummary(**defaults)


def make_history_record(
    history_id: str = "hist-0001",
    request_id: str = "req-0001",
    user_id: str = "user-0001",
    status: PredictionHistoryStatus = PredictionHistoryStatus.SUCCESS,
    created_at: str = "2026-07-27T10:00:00+00:00",
    metadata: PredictionHistoryMetadata | None = None,
    summary: PredictionHistorySummary | None = None,
) -> PredictionHistory:
    return PredictionHistory(
        history_id=history_id,
        request_id=request_id,
        user_id=user_id,
        status=status,
        created_at=created_at,
        metadata=metadata or make_metadata(request_id=request_id, user_id=user_id),
        summary=summary if summary is not None else make_summary(),
    )
