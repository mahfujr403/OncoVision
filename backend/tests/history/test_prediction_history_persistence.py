"""Tests for Phase 5.2 Prediction History Persistence (ADR-033).

Covers what this phase introduces on top of the Phase 5.1 skeleton:
    - `PredictionHistoryService.persist()` now actually delegates to the
      repository, and wraps any repository failure in a
      `PredictionHistoryPersistenceError`.
    - `PredictionService._execute_history_stage` -- the HISTORY pipeline
      stage wired into `PredictionService.predict()` -- persists when
      `save_history` is true and a `history_service` was supplied, skips
      when either is not, and never raises when persistence fails
      (ADR-033's core guarantee: a database failure must never fail the
      originating prediction request).

Does NOT cover History Retrieval or Pagination/Filtering (Phase 5.3/5.4),
and does not exercise a real database -- persistence failures are
simulated with an in-memory fake repository, consistent with the rest of
the Phase 5.1 test suite.
"""

import asyncio

import pytest

from app.core.upload import UploadValidator
from app.history.exceptions import PredictionHistoryPersistenceError
from app.history.prediction_history import PredictionHistory
from app.services.prediction_history_service import PredictionHistoryService
from app.services.prediction_result import PipelineStageName, PipelineStageStatus
from app.services.prediction_service import PredictionService
from tests.history.conftest_helpers import (
    make_context,
    make_individual_prediction,
    make_response_result,
)
from tests.history.test_prediction_history_repository import InMemoryPredictionHistoryRepository


class FailingPredictionHistoryRepository(InMemoryPredictionHistoryRepository):
    """A fake repository whose `save()` always fails, simulating a database outage."""

    async def save(self, history: PredictionHistory) -> PredictionHistory:
        raise RuntimeError("simulated database connection failure")


class TrackingPredictionHistoryRepository(InMemoryPredictionHistoryRepository):
    """A fake repository that records whether `save()` was ever invoked."""

    def __init__(self) -> None:
        super().__init__()
        self.save_calls: list[PredictionHistory] = []

    async def save(self, history: PredictionHistory) -> PredictionHistory:
        self.save_calls.append(history)
        return await super().save(history)


class TestPredictionHistoryServicePersist:
    """Verifies `PredictionHistoryService.persist()` (Phase 5.2, ADR-033)."""

    def test_persist_saves_via_the_repository_and_returns_the_history(self) -> None:
        repository = TrackingPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)
        context = make_context()
        history = service.prepare_history_record(
            prediction_result=_prediction_result_stub(),
            context=context,
        )

        persisted = asyncio.run(service.persist(history))

        assert persisted == history
        assert repository.save_calls == [history]

    def test_persist_wraps_repository_failures_as_persistence_error(self) -> None:
        repository = FailingPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)
        context = make_context()
        history = service.prepare_history_record(
            prediction_result=_prediction_result_stub(),
            context=context,
        )

        with pytest.raises(PredictionHistoryPersistenceError):
            asyncio.run(service.persist(history))

    def test_persist_failure_chains_the_original_exception(self) -> None:
        repository = FailingPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)
        context = make_context()
        history = service.prepare_history_record(
            prediction_result=_prediction_result_stub(),
            context=context,
        )

        try:
            asyncio.run(service.persist(history))
        except PredictionHistoryPersistenceError as exc:
            assert isinstance(exc.__cause__, RuntimeError)
        else:
            pytest.fail("Expected PredictionHistoryPersistenceError to be raised.")


class TestPredictionServiceHistoryStage:
    """Verifies the HISTORY pipeline stage wired into `PredictionService` (Phase 5.2, ADR-033)."""

    @staticmethod
    def _prediction_service() -> PredictionService:
        return PredictionService(upload_validator=UploadValidator())

    def test_history_stage_persists_when_save_history_is_true(self) -> None:
        service = self._prediction_service()
        repository = TrackingPredictionHistoryRepository()
        history_service = PredictionHistoryService(repository=repository)
        context = make_context()  # save_history=True by default (conftest_helpers)
        response_result = make_response_result()
        stages: list = []

        history_reference = asyncio.run(
            service._execute_history_stage(
                context=context,
                stages=stages,
                response_result=response_result,
                individual_model_results=[make_individual_prediction()],
                execution_stats=None,
                runtime_metadata=None,
                history_service=history_service,
            )
        )

        assert history_reference is not None
        assert len(repository.save_calls) == 1
        assert repository.save_calls[0].history_id == history_reference

        history_stage = next(s for s in stages if s.name == PipelineStageName.HISTORY)
        assert history_stage.status == PipelineStageStatus.COMPLETED

    def test_history_stage_skips_when_save_history_is_false(self) -> None:
        service = self._prediction_service()
        repository = TrackingPredictionHistoryRepository()
        history_service = PredictionHistoryService(repository=repository)
        context = make_context(options=make_context().options.model_copy(update={"save_history": False}))
        stages: list = []

        history_reference = asyncio.run(
            service._execute_history_stage(
                context=context,
                stages=stages,
                response_result=make_response_result(),
                individual_model_results=None,
                execution_stats=None,
                runtime_metadata=None,
                history_service=history_service,
            )
        )

        assert history_reference is None
        assert repository.save_calls == []

        history_stage = next(s for s in stages if s.name == PipelineStageName.HISTORY)
        assert history_stage.status == PipelineStageStatus.SKIPPED

    def test_history_stage_skips_when_no_history_service_supplied(self) -> None:
        service = self._prediction_service()
        context = make_context()
        stages: list = []

        history_reference = asyncio.run(
            service._execute_history_stage(
                context=context,
                stages=stages,
                response_result=make_response_result(),
                individual_model_results=None,
                execution_stats=None,
                runtime_metadata=None,
                history_service=None,
            )
        )

        assert history_reference is None
        history_stage = next(s for s in stages if s.name == PipelineStageName.HISTORY)
        assert history_stage.status == PipelineStageStatus.SKIPPED

    def test_history_stage_persistence_failure_is_swallowed_gracefully(self) -> None:
        """Per ADR-033: a database failure must never fail the prediction request."""
        service = self._prediction_service()
        repository = FailingPredictionHistoryRepository()
        history_service = PredictionHistoryService(repository=repository)
        context = make_context()
        stages: list = []

        history_reference = asyncio.run(
            service._execute_history_stage(
                context=context,
                stages=stages,
                response_result=make_response_result(),
                individual_model_results=None,
                execution_stats=None,
                runtime_metadata=None,
                history_service=history_service,
            )
        )

        # No exception propagated, response is still usable, stage recorded as skipped.
        assert history_reference is None
        history_stage = next(s for s in stages if s.name == PipelineStageName.HISTORY)
        assert history_stage.status == PipelineStageStatus.SKIPPED
        assert "failed" in history_stage.detail.lower()

    def test_predict_accepts_a_missing_history_service_without_error(self) -> None:
        """`predict()` must remain callable by pre-Phase-5.2 callers (backward compatibility)."""
        import inspect

        signature = inspect.signature(PredictionService.predict)
        assert signature.parameters["history_service"].default is None


def _prediction_result_stub():
    from tests.history.conftest_helpers import make_prediction_result

    return make_prediction_result(response_result=make_response_result())
