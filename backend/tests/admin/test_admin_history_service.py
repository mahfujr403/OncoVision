"""Unit tests for `AdminHistoryService` (Phase 7.4, ADR-036).

Exercises the service (via the real `PredictionHistoryService`, per
ADR-036's "reuse Phase 5, do not create a second history implementation")
against `AdminAwarePredictionHistoryRepository`
(`tests/admin/doubles.py`) -- no real database.
"""

import asyncio

from app.history.enums import PredictionHistoryStatus
from app.history.filters import PredictionHistoryFilter
from app.history.metadata import PredictionHistoryMetadata
from app.history.pagination import PredictionHistoryPageRequest
from app.history.prediction_history import PredictionHistory
from app.history.summary import PredictionHistorySummary
from app.services.admin_history_service import AdminHistoryService
from app.services.prediction_history_service import PredictionHistoryService
from tests.admin.doubles import AdminAwarePredictionHistoryRepository
from tests.history.conftest_helpers import make_context


def _make_history(
    user_id: str,
    history_id: str,
    status: PredictionHistoryStatus = PredictionHistoryStatus.SUCCESS,
) -> PredictionHistory:
    context = make_context(user_id=user_id)
    metadata = PredictionHistoryMetadata(
        request_id=context.request_id,
        requested_at=context.requested_at,
        user_id=user_id,
        user_email=context.user_email,
        image_filename=context.image_filename,
        image_content_type=context.image_content_type,
        image_size_bytes=context.image_size_bytes,
        image_width=context.image_width,
        image_height=context.image_height,
    )
    summary = PredictionHistorySummary(
        predicted_class="lung_aca",
        confidence=91.2,
        agreement_ratio=1.0,
        successful_models=["mobilenetv2"],
        failed_models=[],
        participating_models=1,
        individual_predictions=[],
    )
    return PredictionHistory(
        history_id=history_id,
        request_id=context.request_id,
        user_id=user_id,
        status=status,
        created_at="2026-07-27T10:00:00+00:00",
        metadata=metadata,
        summary=summary,
    )


def _service(records: list[PredictionHistory]) -> AdminHistoryService:
    repository = AdminAwarePredictionHistoryRepository(records)
    history_service = PredictionHistoryService(repository)
    return AdminHistoryService(history_service)


class TestListHistory:
    def test_lists_records_across_every_user_by_default(self) -> None:
        records = [
            _make_history("user-a", "hist-1"),
            _make_history("user-b", "hist-2"),
        ]
        service = _service(records)

        page = asyncio.run(
            service.list_history(PredictionHistoryPageRequest(page=1, page_size=10))
        )

        assert page.metadata.total_records == 2
        assert {item.history_id for item in page.items} == {"hist-1", "hist-2"}

    def test_narrows_to_a_single_user_when_user_id_supplied(self) -> None:
        records = [
            _make_history("user-a", "hist-1"),
            _make_history("user-b", "hist-2"),
        ]
        service = _service(records)

        page = asyncio.run(
            service.list_history(
                PredictionHistoryPageRequest(page=1, page_size=10), user_id="user-a"
            )
        )

        assert page.metadata.total_records == 1
        assert page.items[0].history_id == "hist-1"

    def test_applies_status_filter_across_users(self) -> None:
        records = [
            _make_history("user-a", "hist-1", status=PredictionHistoryStatus.SUCCESS),
            _make_history("user-b", "hist-2", status=PredictionHistoryStatus.FAILED),
        ]
        service = _service(records)

        page = asyncio.run(
            service.list_history(
                PredictionHistoryPageRequest(page=1, page_size=10),
                filters=PredictionHistoryFilter(status=PredictionHistoryStatus.FAILED),
            )
        )

        assert page.metadata.total_records == 1
        assert page.items[0].history_id == "hist-2"

    def test_pagination_metadata_reflects_full_result_set(self) -> None:
        records = [_make_history("user-a", f"hist-{i}") for i in range(5)]
        service = _service(records)

        page = asyncio.run(
            service.list_history(PredictionHistoryPageRequest(page=1, page_size=2))
        )

        assert len(page.items) == 2
        assert page.metadata.total_records == 5
        assert page.metadata.total_pages == 3
        assert page.metadata.has_next is True
        assert page.metadata.has_previous is False


class TestGetHistory:
    def test_retrieves_record_regardless_of_owner(self) -> None:
        records = [_make_history("user-a", "hist-1")]
        service = _service(records)

        result = asyncio.run(service.get_history("hist-1"))

        assert result is not None
        assert result.user_id == "user-a"

    def test_nonexistent_record_returns_none(self) -> None:
        service = _service([])

        result = asyncio.run(service.get_history("does-not-exist"))

        assert result is None
