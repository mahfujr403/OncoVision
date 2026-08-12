"""Tests for Phase 5.5 Prediction History Detail Retrieval (ADR-035 update).

Covers what this phase introduces on top of Phase 5.1-5.4:
    - `SQLAlchemyPredictionHistoryRepository.get_by_id()` -- single-record,
      user-scoped lookup by primary key, exercised against a lightweight
      mocked `AsyncSession` rather than a real PostgreSQL instance.
    - `PredictionHistoryService.get_history()` -- delegates to the
      repository without performing any lookup or ownership logic of its
      own.

Does not cover the HTTP-level endpoint; see
`tests/api/test_prediction_history_detail_router.py` for router-level
coverage (authentication, 404 translation, response shape).
"""

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.history.enums import PredictionHistoryStatus
from app.history.metadata import PredictionHistoryMetadata
from app.history.prediction_history import PredictionHistory
from app.history.summary import PredictionHistorySummary
from app.repositories.prediction_history_repository import SQLAlchemyPredictionHistoryRepository
from app.services.prediction_history_service import PredictionHistoryService
from tests.history.conftest_helpers import make_context
from tests.history.test_prediction_history_repository import InMemoryPredictionHistoryRepository


def _make_record(record_id: uuid.UUID, user_id: uuid.UUID) -> SimpleNamespace:
    """Build a lightweight ORM-shaped fake, mirroring `test_prediction_history_retrieval.py`."""
    context = make_context(user_id=str(user_id))
    metadata = PredictionHistoryMetadata(
        request_id=context.request_id,
        requested_at=context.requested_at,
        user_id=str(user_id),
        user_email=context.user_email,
        image_filename=context.image_filename,
        image_content_type=context.image_content_type,
        image_size_bytes=context.image_size_bytes,
        image_width=context.image_width,
        image_height=context.image_height,
        model_manifest_version="2026.07.1",
        processing_time_ms=154.8,
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

    return SimpleNamespace(
        id=record_id,
        request_id=context.request_id,
        user_id=user_id,
        status=PredictionHistoryStatus.SUCCESS,
        history_metadata=metadata.model_dump(mode="json"),
        summary=summary.model_dump(mode="json"),
        created_at=datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc),
    )


class _FakeScalars:
    def __init__(self, record) -> None:
        self._record = record

    def first(self):
        return self._record


class _FakeExecuteResult:
    def __init__(self, record) -> None:
        self._record = record

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._record)


class _FakeAsyncSession:
    """Minimal `AsyncSession` stand-in, mirroring `test_prediction_history_retrieval.py`."""

    def __init__(self, record) -> None:
        self._record = record
        self.executed_statements: list = []

    async def execute(self, statement):
        self.executed_statements.append(statement)
        return _FakeExecuteResult(self._record)


class TestSQLAlchemyPredictionHistoryRepositoryGetById:
    """Verifies `SQLAlchemyPredictionHistoryRepository.get_by_id()` (Phase 5.5, ADR-035 update)."""

    def test_get_by_id_returns_the_matching_history_when_owned_by_the_caller(self) -> None:
        owner_id = uuid.uuid4()
        record_id = uuid.uuid4()
        record = _make_record(record_id, owner_id)
        session = _FakeAsyncSession(record)
        repository = SQLAlchemyPredictionHistoryRepository(session)

        result = asyncio.run(
            repository.get_by_id(history_id=str(record_id), user_id=str(owner_id))
        )

        assert isinstance(result, PredictionHistory)
        assert result.history_id == str(record_id)
        assert result.user_id == str(owner_id)
        assert len(session.executed_statements) == 1

    def test_get_by_id_returns_none_when_no_record_matches(self) -> None:
        session = _FakeAsyncSession(record=None)
        repository = SQLAlchemyPredictionHistoryRepository(session)

        result = asyncio.run(
            repository.get_by_id(history_id=str(uuid.uuid4()), user_id=str(uuid.uuid4()))
        )

        assert result is None

    def test_get_by_id_returns_none_for_malformed_history_id(self) -> None:
        session = _FakeAsyncSession(record=None)
        repository = SQLAlchemyPredictionHistoryRepository(session)

        result = asyncio.run(
            repository.get_by_id(history_id="not-a-uuid", user_id=str(uuid.uuid4()))
        )

        assert result is None
        # The malformed identifier must be rejected before any query runs.
        assert session.executed_statements == []

    def test_get_by_id_returns_none_for_malformed_user_id(self) -> None:
        session = _FakeAsyncSession(record=None)
        repository = SQLAlchemyPredictionHistoryRepository(session)

        result = asyncio.run(
            repository.get_by_id(history_id=str(uuid.uuid4()), user_id="not-a-uuid")
        )

        assert result is None
        assert session.executed_statements == []


class TestPredictionHistoryServiceGetHistory:
    """Verifies `PredictionHistoryService.get_history()` (Phase 5.5, ADR-035 update)."""

    def test_get_history_delegates_to_the_repository(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)
        context = make_context(user_id="user-0001")

        async def seed() -> PredictionHistory:
            history = PredictionHistory(
                history_id="hist-0001",
                request_id=context.request_id,
                user_id="user-0001",
                status=PredictionHistoryStatus.SUCCESS,
                created_at="2026-07-27T10:00:00+00:00",
                metadata=PredictionHistoryMetadata(
                    request_id=context.request_id,
                    requested_at=context.requested_at,
                    user_id="user-0001",
                    user_email=context.user_email,
                    image_filename=context.image_filename,
                    image_content_type=context.image_content_type,
                    image_size_bytes=context.image_size_bytes,
                    image_width=context.image_width,
                    image_height=context.image_height,
                ),
                summary=PredictionHistorySummary.empty(),
            )
            return await repository.save(history)

        asyncio.run(seed())

        result = asyncio.run(service.get_history(history_id="hist-0001", user_id="user-0001"))

        assert result is not None
        assert result.history_id == "hist-0001"

    def test_get_history_returns_none_when_owned_by_a_different_user(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)
        context = make_context(user_id="owner-0001")

        async def seed() -> None:
            await repository.save(
                PredictionHistory(
                    history_id="hist-0001",
                    request_id=context.request_id,
                    user_id="owner-0001",
                    status=PredictionHistoryStatus.SUCCESS,
                    created_at="2026-07-27T10:00:00+00:00",
                    metadata=PredictionHistoryMetadata(
                        request_id=context.request_id,
                        requested_at=context.requested_at,
                        user_id="owner-0001",
                        user_email=context.user_email,
                        image_filename=context.image_filename,
                        image_content_type=context.image_content_type,
                        image_size_bytes=context.image_size_bytes,
                        image_width=context.image_width,
                        image_height=context.image_height,
                    ),
                    summary=PredictionHistorySummary.empty(),
                )
            )

        asyncio.run(seed())

        result = asyncio.run(
            service.get_history(history_id="hist-0001", user_id="someone-else")
        )

        assert result is None

    def test_get_history_returns_none_when_no_record_matches(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)

        result = asyncio.run(service.get_history(history_id="missing", user_id="user-0001"))

        assert result is None
