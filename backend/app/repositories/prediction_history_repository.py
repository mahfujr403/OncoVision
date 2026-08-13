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
service depends only on this abstract contract).

Phase 5.3 (History Retrieval, ADR-034) additionally implements
`list_by_user()`: a read-only, user-scoped, newest-first query that
returns domain-level `PredictionHistory` objects via
`PredictionHistoryMapper.to_domain()`. `get_by_id()` remained
unimplemented as of Phase 5.3, reserved for a future History Detail API.

Phase 5.4 (History Pagination & Filtering, ADR-035) extends
`list_by_user()` with an optional `filters` parameter and implements
`count_by_user()`, so both share a single, reusable predicate-building
helper (`_apply_filters()`) and can never drift out of sync with each
other. Ownership continues to be enforced by filtering on `user_id`
directly in each query -- `filters` never carries a `user_id` of its
own (`app.history.filters.PredictionHistoryFilter`), so a caller cannot
use filtering to widen a query beyond its own records.

Phase 5.5 (History Detail Retrieval, ADR-035 update) implements
`get_by_id()`: a single-record, user-scoped lookup by primary key.
Ownership is enforced the same way it already is for `list_by_user()` /
`count_by_user()` -- by filtering on `user_id` directly in the query --
so a record owned by another user is indistinguishable from a
non-existent one at this layer; both simply return `None`. Reuses the
same `_parse_user_id()` malformed-identifier handling already
established by Phase 5.3/5.4, extended with an equivalent
`_parse_history_id()` for the record's own primary key.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.history.filters import PredictionHistoryFilter
from app.history.mapper import PredictionHistoryMapper
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

        Implemented by Phase 5.5 (History Detail Retrieval, ADR-035
        update). `user_id` is required on every lookup so ownership is
        enforced at the repository boundary, not left to callers -- a
        record that exists but is owned by a different user returns
        `None`, exactly as a genuinely missing record would.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        limit: int,
        offset: int,
        filters: PredictionHistoryFilter | None = None,
    ) -> list[PredictionHistory]:
        """Return a page of history records owned by `user_id`, newest first.

        `filters` (Phase 5.4, ADR-035) is optional and, when supplied,
        narrows the result set further -- ownership by `user_id` remains
        enforced independently of, and prior to, any filter predicate.
        """
        raise NotImplementedError

    @abstractmethod
    async def count_by_user(
        self,
        user_id: str,
        filters: PredictionHistoryFilter | None = None,
    ) -> int:
        """Return the total number of history records owned by `user_id`.

        Supports pagination metadata alongside `list_by_user` (Phase 5.4,
        ADR-035). `filters`, when supplied, must apply the exact same
        predicates as the corresponding `list_by_user()` call so the
        reported `total_records` always matches what `list_by_user()`
        would return across every page.
        """
        raise NotImplementedError

    # -- Phase 7.4 (Administrative Prediction/History Oversight, ADR-036) --
    #
    # The three methods below support read-only, cross-user administrative
    # oversight. They are intentionally NOT declared with `@abstractmethod`:
    # every pre-Phase-7 concrete/fake implementation of this contract
    # (`SQLAlchemyPredictionHistoryRepository` and the various in-memory
    # test doubles under `tests/`) predates them and must keep working
    # unmodified. Each method's default body raises `NotImplementedError`
    # so callers that genuinely need admin-scoped access get an explicit,
    # unambiguous failure rather than silently misbehaving; the concrete
    # SQLAlchemy repository below overrides all three for real.
    #
    # None of these methods narrow ownership on the caller's behalf --
    # unlike `list_by_user()`/`get_by_id()`, they are permitted to return
    # records across every user. Restricting who may invoke them is an
    # authorization concern enforced upstream by `require_admin`
    # (`app.dependencies.auth`), never by this repository.

    async def list_all(
        self,
        limit: int,
        offset: int,
        filters: PredictionHistoryFilter | None = None,
        user_id: str | None = None,
    ) -> list[PredictionHistory]:
        """Return one page of history records across every user, newest first.

        `user_id`, when supplied, narrows the result set to a single
        user's records without changing the underlying query shape --
        letting administrative oversight inspect either the full history
        table or one user's own history through the same method.
        """
        raise NotImplementedError

    async def count_all(
        self,
        filters: PredictionHistoryFilter | None = None,
        user_id: str | None = None,
    ) -> int:
        """Return the total number of history records matching `filters`/`user_id`.

        Mirrors `count_by_user()`'s role for `list_by_user()`: applies the
        exact same predicates as the corresponding `list_all()` call so
        pagination metadata stays consistent.
        """
        raise NotImplementedError

    async def get_by_id_unscoped(self, history_id: str) -> PredictionHistory | None:
        """Return a single history record by primary key, regardless of owner.

        Unlike `get_by_id()`, performs no `user_id` ownership check --
        reserved for administrative detail retrieval, where the caller's
        authorization has already been established by `require_admin`.
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

    def __init__(
        self,
        session: AsyncSession,
        mapper: PredictionHistoryMapper | None = None,
    ) -> None:
        self._session = session
        self._mapper = mapper or PredictionHistoryMapper()

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
        """Return a single history record owned by `user_id` (Phase 5.5, ADR-035 update).

        Queries `PredictionHistoryRecord` by primary key, scoped to
        `user_id` in the same `WHERE` clause -- exactly the same
        ownership-at-the-query-boundary approach `list_by_user()` /
        `count_by_user()` already use. A record that exists but is owned
        by a different user is therefore indistinguishable from a
        genuinely missing one: both simply return `None`, and it is the
        caller's responsibility (`PredictionHistoryService.get_history()`)
        to translate that into a `PredictionHistoryNotFoundError` (404).

        The single matching row, if any, is translated into an immutable
        `PredictionHistory` domain object via
        `PredictionHistoryMapper.to_domain()` -- no `PredictionHistoryRecord`
        ever leaves this repository.

        Args:
            history_id: Identifier of the history record to retrieve.
                Must be a valid UUID string.
            user_id: Identifier of the authenticated user who must own
                `history_id`. Must be a valid UUID string.

        Returns:
            The matching `PredictionHistory`, or `None` when no such
            record exists, `history_id`/`user_id` is owned by a different
            user, or either identifier is not a well-formed UUID.
        """
        record_id = self._parse_history_id(history_id)
        owner_id = self._parse_user_id(user_id, operation="detail retrieval")
        if record_id is None or owner_id is None:
            return None

        statement = select(PredictionHistoryRecord).where(
            PredictionHistoryRecord.id == record_id,
            PredictionHistoryRecord.user_id == owner_id,
        )

        result = await self._session.execute(statement)
        record = result.scalars().first()

        if record is None:
            logger.info(
                "Prediction history detail lookup found no matching record: "
                "history_id=%s user_id=%s",
                history_id,
                user_id,
            )
            return None

        logger.info(
            "Prediction history detail record retrieved from database: "
            "history_id=%s user_id=%s",
            history_id,
            user_id,
        )

        return self._mapper.to_domain(record)

    async def list_by_user(
        self,
        user_id: str,
        limit: int,
        offset: int,
        filters: PredictionHistoryFilter | None = None,
    ) -> list[PredictionHistory]:
        """Return a page of history records owned by `user_id`, newest first (Phase 5.3/5.4, ADR-034/035).

        Queries `PredictionHistoryRecord` filtered by `user_id`, ordered by
        `created_at` descending (newest first, per ADR-034/ADR-035's
        Ordering Rules), and bounded by `limit`/`offset`. Every row is
        translated into an immutable `PredictionHistory` domain object via
        `PredictionHistoryMapper.to_domain()` -- no `PredictionHistoryRecord`
        ever leaves this repository. Ownership is enforced here, at the
        repository boundary, by filtering on `user_id` directly in the
        query rather than post-filtering results in the service layer.

        `filters` (Phase 5.4, ADR-035) is applied through `_apply_filters()`
        after the ownership predicate, so filtering can only ever narrow
        `user_id`'s own results -- never widen a query beyond them.

        Args:
            user_id: Identifier of the authenticated user whose history is
                being retrieved. Must be a valid UUID string.
            limit: Maximum number of records to return.
            offset: Number of newest-first records to skip before
                collecting `limit` results.
            filters: Optional `PredictionHistoryFilter` narrowing the
                result set by status, predicted class, date range, or
                confidence range. `None` (the default) applies no
                additional filtering.

        Returns:
            A list of `PredictionHistory` domain objects, newest first.
            An empty list when `user_id` has no matching history records,
            or `user_id` is not a well-formed UUID.
        """
        owner_id = self._parse_user_id(user_id, operation="list retrieval")
        if owner_id is None:
            return []

        statement = self._apply_filters(
            select(PredictionHistoryRecord).where(PredictionHistoryRecord.user_id == owner_id),
            filters,
        )
        statement = statement.order_by(PredictionHistoryRecord.created_at.desc())
        statement = statement.limit(limit).offset(offset)

        result = await self._session.execute(statement)
        records = result.scalars().all()

        logger.info(
            "Prediction history list retrieved from database: user_id=%s "
            "record_count=%d limit=%d offset=%d filtered=%s",
            user_id,
            len(records),
            limit,
            offset,
            filters is not None and not filters.is_empty,
        )

        return [self._mapper.to_domain(record) for record in records]

    async def count_by_user(
        self,
        user_id: str,
        filters: PredictionHistoryFilter | None = None,
    ) -> int:
        """Return the total number of history records owned by `user_id` (Phase 5.4, ADR-035).

        Applies the exact same ownership predicate and, via
        `_apply_filters()`, the exact same filter predicates as
        `list_by_user()` -- built from the same helper so the two can
        never drift out of sync -- so the returned total always matches
        what `list_by_user()` would return across every page for the same
        `user_id`/`filters` pair.

        Args:
            user_id: Identifier of the authenticated user whose history is
                being counted. Must be a valid UUID string.
            filters: Optional `PredictionHistoryFilter` matching the one
                passed to the corresponding `list_by_user()` call.

        Returns:
            The total number of matching records. `0` when `user_id` has
            no matching history records, or `user_id` is not a
            well-formed UUID.
        """
        owner_id = self._parse_user_id(user_id, operation="count retrieval")
        if owner_id is None:
            return 0

        statement = self._apply_filters(
            select(func.count(PredictionHistoryRecord.id)).where(
                PredictionHistoryRecord.user_id == owner_id
            ),
            filters,
        )

        result = await self._session.execute(statement)
        total = result.scalar_one()

        logger.info(
            "Prediction history count retrieved from database: user_id=%s "
            "total_records=%d filtered=%s",
            user_id,
            total,
            filters is not None and not filters.is_empty,
        )

        return total

    async def list_all(
        self,
        limit: int,
        offset: int,
        filters: PredictionHistoryFilter | None = None,
        user_id: str | None = None,
    ) -> list[PredictionHistory]:
        """Return one page of history records across every user, newest first (Phase 7.4, ADR-036).

        Mirrors `list_by_user()` exactly, except the `user_id` ownership
        predicate is applied only when a caller explicitly supplies one
        (narrowing administrative oversight to a single user) rather than
        unconditionally. `filters` is applied through the same
        `_apply_filters()` helper `list_by_user()`/`count_by_user()`
        already use, so all three query paths can never drift out of sync.
        """
        statement = select(PredictionHistoryRecord)

        if user_id is not None:
            owner_id = self._parse_user_id(user_id, operation="admin list retrieval")
            if owner_id is None:
                return []
            statement = statement.where(PredictionHistoryRecord.user_id == owner_id)

        statement = self._apply_filters(statement, filters)
        statement = statement.order_by(PredictionHistoryRecord.created_at.desc())
        statement = statement.limit(limit).offset(offset)

        result = await self._session.execute(statement)
        records = result.scalars().all()

        logger.info(
            "Administrative prediction history list retrieved from database: "
            "user_id=%s record_count=%d limit=%d offset=%d filtered=%s",
            user_id,
            len(records),
            limit,
            offset,
            filters is not None and not filters.is_empty,
        )

        return [self._mapper.to_domain(record) for record in records]

    async def count_all(
        self,
        filters: PredictionHistoryFilter | None = None,
        user_id: str | None = None,
    ) -> int:
        """Return the total number of history records matching `filters`/`user_id` (Phase 7.4, ADR-036).

        Applies the exact same predicates as `list_all()` -- built from
        the same `_apply_filters()` helper -- so the returned total always
        matches what `list_all()` would return across every page for the
        same `filters`/`user_id` pair.
        """
        statement = select(func.count(PredictionHistoryRecord.id))

        if user_id is not None:
            owner_id = self._parse_user_id(user_id, operation="admin count retrieval")
            if owner_id is None:
                return 0
            statement = statement.where(PredictionHistoryRecord.user_id == owner_id)

        statement = self._apply_filters(statement, filters)

        result = await self._session.execute(statement)
        total = result.scalar_one()

        logger.info(
            "Administrative prediction history count retrieved from database: "
            "user_id=%s total_records=%d filtered=%s",
            user_id,
            total,
            filters is not None and not filters.is_empty,
        )

        return total

    async def get_by_id_unscoped(self, history_id: str) -> PredictionHistory | None:
        """Return a single history record by primary key, regardless of owner (Phase 7.4, ADR-036).

        Identical to `get_by_id()` except no `user_id` predicate is
        applied -- reserved for administrative detail retrieval, where
        authorization has already been established by `require_admin`
        (`app.dependencies.auth`) before this method is ever called.
        """
        record_id = self._parse_history_id(history_id)
        if record_id is None:
            return None

        statement = select(PredictionHistoryRecord).where(
            PredictionHistoryRecord.id == record_id
        )

        result = await self._session.execute(statement)
        record = result.scalars().first()

        if record is None:
            logger.info(
                "Administrative prediction history detail lookup found no matching "
                "record: history_id=%s",
                history_id,
            )
            return None

        logger.info(
            "Administrative prediction history detail record retrieved from "
            "database: history_id=%s",
            history_id,
        )

        return self._mapper.to_domain(record)

    @staticmethod
    def _parse_user_id(user_id: str, operation: str) -> uuid.UUID | None:
        """Parse `user_id` into a UUID, or `None` (logged) when malformed."""
        try:
            return uuid.UUID(user_id)
        except (ValueError, TypeError, AttributeError):
            logger.warning(
                "Prediction history %s received a malformed user_id.", operation
            )
            return None

    @staticmethod
    def _parse_history_id(history_id: str) -> uuid.UUID | None:
        """Parse `history_id` into a UUID, or `None` (logged) when malformed.

        Mirrors `_parse_user_id()` for the record's own primary key
        (Phase 5.5, ADR-035 update).
        """
        try:
            return uuid.UUID(history_id)
        except (ValueError, TypeError, AttributeError):
            logger.warning(
                "Prediction history detail retrieval received a malformed history_id."
            )
            return None

    @staticmethod
    def _apply_filters(statement: Select, filters: PredictionHistoryFilter | None) -> Select:
        """Apply `filters`' optional predicates onto `statement`.

        Shared by `list_by_user()` and `count_by_user()` so both queries
        can never apply a different predicate set for the same `filters`
        value (Phase 5.4, ADR-035). Every predicate is independently
        optional -- only fields actually set on `filters` add a `WHERE`
        clause. Never touches `user_id`; ownership is applied by the
        caller before this helper runs.
        """
        if filters is None or filters.is_empty:
            return statement

        if filters.status is not None:
            statement = statement.where(PredictionHistoryRecord.status == filters.status)

        if filters.predicted_class is not None:
            statement = statement.where(
                PredictionHistoryRecord.predicted_class == filters.predicted_class
            )

        if filters.start_date is not None:
            statement = statement.where(PredictionHistoryRecord.created_at >= filters.start_date)

        if filters.end_date is not None:
            statement = statement.where(PredictionHistoryRecord.created_at <= filters.end_date)

        if filters.min_confidence is not None:
            statement = statement.where(
                PredictionHistoryRecord.confidence >= filters.min_confidence
            )

        if filters.max_confidence is not None:
            statement = statement.where(
                PredictionHistoryRecord.confidence <= filters.max_confidence
            )

        return statement

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
