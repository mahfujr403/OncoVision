"""Prediction History repository contract and implementation.

`PredictionHistoryRepository` defines the persistence contract for
`PredictionHistory` records without containing any database access
itself (Phase 5.1, ADR-032). Mirrors the ABC-based interface convention
already used by `app.ml.ensemble.strategy.EnsembleVotingStrategy`.

Per ADR-032, Prediction History persistence is completely independent
from the Prediction Engine, and history records are append-only: no
method on this contract updates an existing record. Per ADR-033,
`save()` is expected to be called only after the originating prediction
request has already completed successfully, and a persistence failure
must never be allowed to fail that request.

`SQLAlchemyPredictionHistoryRepository` is Phase 5.2's concrete
implementation of `save()` (ADR-033), backed by the
`app.models.prediction_history.PredictionHistoryRecord` ORM model. It
owns the entire unit of work for a single `save()` call -- add, flush,
and commit -- since `PredictionHistoryService` intentionally never holds
a direct `AsyncSession` reference (ADR-032's dependency direction: the
service depends only on this abstract contract). `get_by_id()`,
`list_by_user()`, and `count_by_user()` remain unimplemented in this
phase, reserved for History Retrieval (Phase 5.3) and Pagination &
Filtering (Phase 5.4).
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.history.prediction_history import PredictionHistory
from app.models.prediction_history import PredictionHistoryRecord

logger = get_logger(__name__)


class PredictionHistoryRepository(ABC):
    """Abstract persistence contract for `PredictionHistory` records.

    Every method is asynchronous to match the application's existing
    SQLAlchemy Async convention (see `app.repositories.user_repository`).
    No method here performs inference, loads AI models, or recalculates
    a prediction (ADR-032).
    """

    @abstractmethod
    async def save(self, history: PredictionHistory) -> PredictionHistory:
        """Persist a new, immutable `PredictionHistory` record.

        Reserved for Phase 5.2 (History Persistence, ADR-033). Existing
        records are never updated -- Prediction History is append-only.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, history_id: str, user_id: str) -> PredictionHistory | None:
        """Return a single history record owned by `user_id`, or `None` if not found.

        Reserved for Phase 5.3 (History Retrieval). `user_id` is required
        on every lookup so ownership is enforced at the repository
        boundary, not left to callers.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        limit: int,
        offset: int,
    ) -> list[PredictionHistory]:
        """Return a page of history records owned by `user_id`, newest first.

        Reserved for Phase 5.4 (History Pagination & Filtering).
        """
        raise NotImplementedError

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        """Return the total number of history records owned by `user_id`.

        Reserved for Phase 5.4 (History Pagination & Filtering), to
        support pagination metadata alongside `list_by_user`.
        """
        raise NotImplementedError


class SQLAlchemyPredictionHistoryRepository(PredictionHistoryRepository):
    """SQLAlchemy Async-backed `PredictionHistoryRepository` (Phase 5.2, ADR-033).

    Persists `PredictionHistory` domain records as
    `PredictionHistoryRecord` rows. Mirrors the constructor-injection
    convention already used by `UserRepository` and
    `RefreshTokenRepository`: a single request-scoped `AsyncSession` is
    supplied by `app.dependencies.services.get_prediction_history_repository`.

    `save()` owns its entire unit of work (add, flush, commit, rollback
    on failure) because -- unlike `UserRepository`/`RefreshTokenRepository`,
    whose callers (`AuthService`) hold the same session and commit
    explicitly -- `PredictionHistoryService` never receives a direct
    `AsyncSession` reference at all (ADR-032). Keeping the transaction
    boundary inside the repository keeps that dependency direction intact
    while still giving `save()` a single, self-contained commit-or-rollback
    outcome for `PredictionHistoryService.persist()` to catch (ADR-033).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, history: PredictionHistory) -> PredictionHistory:
        """Persist a new, immutable `PredictionHistory` record.

        Builds a `PredictionHistoryRecord` row from `history`, commits it
        as a single unit of work, and returns the original domain object
        unchanged -- persistence never mutates or recalculates any field
        of `history` itself (ADR-032).

        Raises:
            Exception: Any database-layer error is rolled back and
                re-raised as-is. `PredictionHistoryService.persist()` is
                responsible for translating this into a
                `PredictionHistoryPersistenceError` and ensuring it never
                fails the originating prediction request (ADR-033).
        """
        record = self._to_record(history)

        try:
            self._session.add(record)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            logger.error(
                "Prediction history database write failed: history_id=%s request_id=%s",
                history.history_id,
                history.request_id,
            )
            raise

        logger.info(
            "Prediction history record persisted to database: history_id=%s request_id=%s "
            "user_id=%s status=%s",
            history.history_id,
            history.request_id,
            history.user_id,
            history.status.value,
        )
        return history

    async def get_by_id(self, history_id: str, user_id: str) -> PredictionHistory | None:
        """Not implemented in this phase.

        Reserved for Phase 5.3 (History Retrieval), which will read a
        `PredictionHistoryRecord` row and translate it back into a
        `PredictionHistory` domain object.
        """
        raise NotImplementedError(
            "Prediction History retrieval begins in Phase 5.3; "
            "SQLAlchemyPredictionHistoryRepository.get_by_id() is not yet implemented."
        )

    async def list_by_user(
        self,
        user_id: str,
        limit: int,
        offset: int,
    ) -> list[PredictionHistory]:
        """Not implemented in this phase.

        Reserved for Phase 5.4 (History Pagination & Filtering).
        """
        raise NotImplementedError(
            "Prediction History pagination begins in Phase 5.4; "
            "SQLAlchemyPredictionHistoryRepository.list_by_user() is not yet implemented."
        )

    async def count_by_user(self, user_id: str) -> int:
        """Not implemented in this phase.

        Reserved for Phase 5.4 (History Pagination & Filtering).
        """
        raise NotImplementedError(
            "Prediction History pagination begins in Phase 5.4; "
            "SQLAlchemyPredictionHistoryRepository.count_by_user() is not yet implemented."
        )

    @staticmethod
    def _to_record(history: PredictionHistory) -> PredictionHistoryRecord:
        """Project an immutable `PredictionHistory` onto a writable ORM row.

        A pure, side-effect-free translation -- every value is copied
        directly from `history`; nothing is recalculated (ADR-032).
        """
        return PredictionHistoryRecord(
            id=uuid.UUID(history.history_id),
            request_id=history.request_id,
            user_id=uuid.UUID(history.user_id),
            status=history.status,
            predicted_class=history.summary.predicted_class,
            confidence=history.summary.confidence,
            agreement_ratio=history.summary.agreement_ratio,
            participating_models=history.summary.participating_models,
            history_metadata=history.metadata.model_dump(mode="json"),
            summary=history.summary.model_dump(mode="json"),
            created_at=datetime.fromisoformat(history.created_at),
        )
