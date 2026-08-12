"""Tests for the Phase 5.1 Prediction History Service skeleton (ADR-032).

Covers only what Phase 5.1 introduces: `PredictionHistoryService` can be
constructed via dependency injection with a `PredictionHistoryRepository`
implementation, and can build (but not persist) a `PredictionHistory`
record.

`persist()` is covered separately by
`tests/history/test_prediction_history_persistence.py` (Phase 5.2,
ADR-033), which exercises the now-real save/skip/failure behaviors.
`get_history()` became real in Phase 5.5 (ADR-035 update); see
`tests/history/test_prediction_history_detail.py` for full coverage --
only a minimal smoke test remains here.
"""

import asyncio

import pytest

from app.history.prediction_history import PredictionHistory
from app.services.prediction_history_service import PredictionHistoryService
from tests.history.conftest_helpers import make_context, make_prediction_result, make_response_result
from tests.history.test_prediction_history_repository import InMemoryPredictionHistoryRepository


@pytest.fixture
def service() -> PredictionHistoryService:
    return PredictionHistoryService(repository=InMemoryPredictionHistoryRepository())


class TestPredictionHistoryServiceSkeleton:
    """Verifies Phase 5.1 introduces only the Prediction History Service skeleton."""

    def test_service_is_constructible_via_dependency_injection(self) -> None:
        repository = InMemoryPredictionHistoryRepository()

        service = PredictionHistoryService(repository=repository)

        assert service is not None

    def test_prepare_history_record_returns_prediction_history(
        self, service: PredictionHistoryService
    ) -> None:
        context = make_context()
        prediction_result = make_prediction_result(response_result=make_response_result())

        history = service.prepare_history_record(
            prediction_result=prediction_result, context=context
        )

        assert isinstance(history, PredictionHistory)

    def test_prepare_history_record_never_calls_the_repository(self) -> None:
        class TrackingRepository(InMemoryPredictionHistoryRepository):
            def __init__(self) -> None:
                super().__init__()
                self.save_called = False

            async def save(self, history: PredictionHistory) -> PredictionHistory:
                self.save_called = True
                return await super().save(history)

        repository = TrackingRepository()
        service = PredictionHistoryService(repository=repository)
        context = make_context()
        prediction_result = make_prediction_result(response_result=make_response_result())

        service.prepare_history_record(prediction_result=prediction_result, context=context)

        assert repository.save_called is False

    def test_get_history_returns_none_when_repository_has_no_matching_record(
        self, service: PredictionHistoryService
    ) -> None:
        """`get_history()` became real in Phase 5.5 (ADR-035 update); see
        `tests/history/test_prediction_history_detail.py` for full coverage."""
        result = asyncio.run(service.get_history(history_id="hist-0001", user_id="user-0001"))

        assert result is None

    def test_list_history_returns_empty_list_when_repository_has_no_records(
        self, service: PredictionHistoryService
    ) -> None:
        """`list_history()` became real in Phase 5.3 (ADR-034); see
        `tests/history/test_prediction_history_retrieval.py` for full coverage."""
        results = asyncio.run(service.list_history(user_id="user-0001", limit=10, offset=0))

        assert results == []
