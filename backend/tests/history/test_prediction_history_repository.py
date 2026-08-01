"""Tests for the Phase 5.1 Prediction History Repository contract (ADR-032).

Covers only that `PredictionHistoryRepository` is an abstract contract
with no concrete implementation in this phase. A concrete,
SQLAlchemy-backed implementation is introduced by Phase 5.2 (ADR-033);
this test suite verifies the contract shape using an in-memory fake, not
a real one.
"""

import asyncio
from datetime import datetime

import pytest

from app.history.filters import PredictionHistoryFilter
from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import PredictionHistoryRepository
from tests.history.conftest_helpers import make_context


class InMemoryPredictionHistoryRepository(PredictionHistoryRepository):
    """Minimal fake used only to verify the abstract contract's shape.

    Not a Phase 5.2 deliverable -- has no bearing on the eventual
    SQLAlchemy-backed implementation. Phase 5.4 (ADR-035) extends this
    fake with `filters` support, applying the same filtering semantics
    (status / predicted_class exact match, inclusive date range on
    `created_at`, inclusive confidence range on `summary.confidence`) as
    `SQLAlchemyPredictionHistoryRepository._apply_filters()`, so it stays
    a faithful in-memory stand-in for Phase 5.4 tests.
    """

    def __init__(self) -> None:
        self._records: dict[str, PredictionHistory] = {}

    async def save(self, history: PredictionHistory) -> PredictionHistory:
        self._records[history.history_id] = history
        return history

    async def get_by_id(self, history_id: str, user_id: str) -> PredictionHistory | None:
        record = self._records.get(history_id)
        if record is not None and record.user_id == user_id:
            return record
        return None

    async def list_by_user(
        self,
        user_id: str,
        limit: int,
        offset: int,
        filters: PredictionHistoryFilter | None = None,
    ) -> list[PredictionHistory]:
        matches = self._matches(user_id, filters)
        return matches[offset : offset + limit]

    async def count_by_user(
        self,
        user_id: str,
        filters: PredictionHistoryFilter | None = None,
    ) -> int:
        return len(self._matches(user_id, filters))

    def _matches(
        self, user_id: str, filters: PredictionHistoryFilter | None
    ) -> list[PredictionHistory]:
        """Apply ownership and (optional) filter predicates, newest first.

        Mirrors `SQLAlchemyPredictionHistoryRepository`'s ordering
        (`created_at` descending) and predicate semantics so this fake
        remains a faithful stand-in across both `list_by_user()` and
        `count_by_user()`.
        """
        matches = [record for record in self._records.values() if record.user_id == user_id]

        if filters is not None and not filters.is_empty:
            matches = [record for record in matches if self._matches_filters(record, filters)]

        return sorted(matches, key=lambda record: record.created_at, reverse=True)

    @staticmethod
    def _matches_filters(record: PredictionHistory, filters: PredictionHistoryFilter) -> bool:
        if filters.status is not None and record.status != filters.status:
            return False

        if (
            filters.predicted_class is not None
            and record.summary.predicted_class != filters.predicted_class
        ):
            return False

        record_created_at = datetime.fromisoformat(record.created_at)

        if filters.start_date is not None and record_created_at < filters.start_date:
            return False

        if filters.end_date is not None and record_created_at > filters.end_date:
            return False

        if filters.min_confidence is not None and record.summary.confidence < filters.min_confidence:
            return False

        if filters.max_confidence is not None and record.summary.confidence > filters.max_confidence:
            return False

        return True


class TestPredictionHistoryRepositoryContract:
    """Verifies Phase 5.1 introduces only the repository contract, not an implementation."""

    def test_repository_cannot_be_instantiated_directly(self) -> None:
        with pytest.raises(TypeError):
            PredictionHistoryRepository()  # type: ignore[abstract]

    def test_fake_repository_satisfies_the_contract(self) -> None:
        repository = InMemoryPredictionHistoryRepository()

        assert isinstance(repository, PredictionHistoryRepository)

    def test_fake_repository_save_and_get_by_id_round_trip(self) -> None:
        from app.history.metadata import PredictionHistoryMetadata

        context = make_context()
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
            user_id=context.user_id,
            created_at="2026-07-27T10:00:00+00:00",
            metadata=metadata,
        )
        repository = InMemoryPredictionHistoryRepository()

        async def scenario() -> PredictionHistory | None:
            await repository.save(history)
            return await repository.get_by_id("hist-0001", context.user_id)

        fetched = asyncio.run(scenario())

        assert fetched == history

    def test_fake_repository_enforces_ownership_on_get_by_id(self) -> None:
        from app.history.metadata import PredictionHistoryMetadata

        context = make_context(user_id="owner-1")
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
            user_id="owner-1",
            created_at="2026-07-27T10:00:00+00:00",
            metadata=metadata,
        )
        repository = InMemoryPredictionHistoryRepository()

        async def scenario() -> PredictionHistory | None:
            await repository.save(history)
            return await repository.get_by_id("hist-0001", "someone-else")

        fetched = asyncio.run(scenario())

        assert fetched is None
