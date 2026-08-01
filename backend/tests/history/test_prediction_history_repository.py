"""Tests for the Phase 5.1 Prediction History Repository contract (ADR-032).

Covers only that `PredictionHistoryRepository` is an abstract contract
with no concrete implementation in this phase. A concrete,
SQLAlchemy-backed implementation is introduced by Phase 5.2 (ADR-033);
this test suite verifies the contract shape using an in-memory fake, not
a real one.
"""

import asyncio

import pytest

from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import PredictionHistoryRepository
from tests.history.conftest_helpers import make_context


class InMemoryPredictionHistoryRepository(PredictionHistoryRepository):
    """Minimal fake used only to verify the abstract contract's shape.

    Not a Phase 5.2 deliverable -- has no bearing on the eventual
    SQLAlchemy-backed implementation.
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
        self, user_id: str, limit: int, offset: int
    ) -> list[PredictionHistory]:
        matches = [record for record in self._records.values() if record.user_id == user_id]
        return matches[offset : offset + limit]

    async def count_by_user(self, user_id: str) -> int:
        return sum(1 for record in self._records.values() if record.user_id == user_id)


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
