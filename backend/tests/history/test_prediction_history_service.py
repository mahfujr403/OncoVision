"""Tests for the Phase 5.1 Prediction History Service skeleton (ADR-032).

Covers only what Phase 5.1 introduces: `PredictionHistoryService` can be
constructed via dependency injection with a `PredictionHistoryRepository`
implementation, and can build (but not persist) a `PredictionHistory`
record. `get_history()` and `list_history()` remain reserved for later
phases (5.3/5.4) and are expected to raise `NotImplementedError` here.

`persist()` is covered separately by
`tests/history/test_prediction_history_persistence.py` (Phase 5.2,
ADR-033), which exercises the now-real save/skip/failure behaviors.
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

    def test_get_history_is_not_yet_implemented(self, service: PredictionHistoryService) -> None:
        with pytest.raises(NotImplementedError):
            asyncio.run(service.get_history(history_id="hist-0001", user_id="user-0001"))

    def test_list_history_is_not_yet_implemented(self, service: PredictionHistoryService) -> None:
        with pytest.raises(NotImplementedError):
            asyncio.run(service.list_history(user_id="user-0001", limit=10, offset=0))
