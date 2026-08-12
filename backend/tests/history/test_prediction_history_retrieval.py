"""Tests for Phase 5.3 Prediction History Retrieval (ADR-034).

Covers what this phase introduces on top of Phase 5.1/5.2:
    - `PredictionHistoryMapper.to_domain()` -- ORM row -> domain object.
    - `SQLAlchemyPredictionHistoryRepository.list_by_user()` -- user-scoped,
      newest-first retrieval, exercised against a lightweight mocked
      `AsyncSession` rather than a real PostgreSQL instance.
    - `PredictionHistoryService.list_history()` -- delegates to the
      repository without performing any filtering of its own.

`get_by_id()` / `get_history()` are not exercised here; they became real
in Phase 5.5 (ADR-035 update) and are covered by
`tests/history/test_prediction_history_detail.py`.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.history.enums import PredictionHistoryStatus
from app.history.mapper import PredictionHistoryMapper
from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import SQLAlchemyPredictionHistoryRepository
from app.services.prediction_history_service import PredictionHistoryService
from tests.history.conftest_helpers import make_context
from tests.history.test_prediction_history_repository import InMemoryPredictionHistoryRepository


def _make_record(
    user_id: uuid.UUID,
    created_at: datetime,
    predicted_class: str = "lung_aca",
) -> SimpleNamespace:
    """Build a lightweight ORM-shaped fake, avoiding a real database dependency.

    Exposes exactly the attributes `PredictionHistoryMapper.to_domain()`
    reads off a `PredictionHistoryRecord` (`id`, `request_id`, `user_id`,
    `status`, `created_at`, `history_metadata`, `summary`), so the mapper
    is exercised for real without requiring SQLAlchemy to round-trip
    through an actual database engine.
    """
    context = make_context(user_id=str(user_id))
    from app.history.metadata import PredictionHistoryMetadata
    from app.history.summary import PredictionHistorySummary

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
    )
    summary = PredictionHistorySummary(
        predicted_class=predicted_class,
        confidence=91.2,
        agreement_ratio=1.0,
        successful_models=["mobilenetv2"],
        failed_models=[],
        participating_models=1,
        individual_predictions=[],
    )

    return SimpleNamespace(
        id=uuid.uuid4(),
        request_id=context.request_id,
        user_id=user_id,
        status=PredictionHistoryStatus.SUCCESS,
        history_metadata=metadata.model_dump(mode="json"),
        summary=summary.model_dump(mode="json"),
        created_at=created_at,
    )


class TestPredictionHistoryMapperToDomain:
    """Verifies `PredictionHistoryMapper.to_domain()` (Phase 5.3, ADR-034)."""

    def test_to_domain_builds_an_equivalent_prediction_history(self) -> None:
        user_id = uuid.uuid4()
        record = _make_record(user_id, datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc))
        mapper = PredictionHistoryMapper()

        history = mapper.to_domain(record)

        assert isinstance(history, PredictionHistory)
        assert history.history_id == str(record.id)
        assert history.request_id == record.request_id
        assert history.user_id == str(user_id)
        assert history.status == PredictionHistoryStatus.SUCCESS
        assert history.summary.predicted_class == "lung_aca"

    def test_to_domain_never_mutates_the_source_record(self) -> None:
        user_id = uuid.uuid4()
        record = _make_record(user_id, datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc))
        original_metadata = dict(record.history_metadata)
        mapper = PredictionHistoryMapper()

        mapper.to_domain(record)

        assert record.history_metadata == original_metadata


class _FakeScalars:
    def __init__(self, records: list) -> None:
        self._records = records

    def all(self) -> list:
        return self._records


class _FakeExecuteResult:
    def __init__(self, records: list) -> None:
        self._records = records

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._records)


class _FakeAsyncSession:
    """Minimal `AsyncSession` stand-in that records the executed statement.

    Avoids requiring a real database engine (e.g. `aiosqlite`, not part of
    the project's runtime dependencies) just to exercise the query-building
    and ORM-to-domain-mapping logic in `list_by_user()`.
    """

    def __init__(self, records: list) -> None:
        self._records = records
        self.executed_statements: list = []

    async def execute(self, statement):
        self.executed_statements.append(statement)
        return _FakeExecuteResult(self._records)


class TestSQLAlchemyPredictionHistoryRepositoryListByUser:
    """Verifies `SQLAlchemyPredictionHistoryRepository.list_by_user()` (Phase 5.3, ADR-034)."""

    def test_list_by_user_maps_every_row_through_the_mapper(self) -> None:
        owner_id = uuid.uuid4()
        records = [
            _make_record(owner_id, datetime(2026, 7, 27, 11, 0, tzinfo=timezone.utc), "lung_n"),
            _make_record(owner_id, datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc), "lung_aca"),
        ]
        session = _FakeAsyncSession(records)
        repository = SQLAlchemyPredictionHistoryRepository(session)

        results = asyncio.run(
            repository.list_by_user(user_id=str(owner_id), limit=10, offset=0)
        )

        assert len(results) == 2
        assert all(isinstance(item, PredictionHistory) for item in results)
        assert all(item.user_id == str(owner_id) for item in results)
        assert [item.summary.predicted_class for item in results] == ["lung_n", "lung_aca"]
        assert len(session.executed_statements) == 1

    def test_list_by_user_returns_empty_list_for_malformed_user_id(self) -> None:
        session = _FakeAsyncSession(records=[])
        repository = SQLAlchemyPredictionHistoryRepository(session)

        results = asyncio.run(
            repository.list_by_user(user_id="not-a-uuid", limit=10, offset=0)
        )

        assert results == []
        # The malformed identifier must be rejected before any query runs.
        assert session.executed_statements == []

    def test_list_by_user_returns_empty_list_when_user_has_no_history(self) -> None:
        session = _FakeAsyncSession(records=[])
        repository = SQLAlchemyPredictionHistoryRepository(session)

        results = asyncio.run(
            repository.list_by_user(user_id=str(uuid.uuid4()), limit=10, offset=0)
        )

        assert results == []


class TestPredictionHistoryServiceListHistory:
    """Verifies `PredictionHistoryService.list_history()` (Phase 5.3, ADR-034)."""

    def test_list_history_delegates_to_the_repository(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)
        context = make_context(user_id="user-0001")
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
            request_id=context.request_id,
            user_id="user-0001",
            created_at="2026-07-27T10:00:00+00:00",
            metadata=metadata,
        )

        async def scenario() -> list[PredictionHistory]:
            await repository.save(history)
            return await service.list_history(user_id="user-0001", limit=10, offset=0)

        results = asyncio.run(scenario())

        assert results == [history]

    def test_list_history_never_returns_another_users_records(self) -> None:
        repository = InMemoryPredictionHistoryRepository()
        service = PredictionHistoryService(repository=repository)

        async def scenario() -> list[PredictionHistory]:
            return await service.list_history(user_id="someone-else", limit=10, offset=0)

        results = asyncio.run(scenario())

        assert results == []
