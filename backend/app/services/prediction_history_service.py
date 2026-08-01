"""Prediction History Service (Phase 5.1 skeleton; Phase 5.2 persistence, ADR-032/ADR-033).

`PredictionHistoryService` is the single orchestration point for
Prediction History, mirroring the role `PredictionService` already plays
for the prediction pipeline (ADR-013). Per ADR-032, it depends only on
the `PredictionHistoryRepository` contract and the `PredictionHistoryMapper`
-- never on `AIRuntimeManager`, `PredictionEngine`, or the database
directly.

Phase 5.1 introduced the SKELETON: `PredictionHistoryService` can build
(but not persist) an immutable `PredictionHistory` record. Phase 5.2
(ADR-033) connects `persist()` for real: it delegates to
`self._repository.save(history)` -- a concrete
`SQLAlchemyPredictionHistoryRepository` supplied through dependency
injection (`app.dependencies.services.get_prediction_history_service`)
-- and translates any repository failure into a
`PredictionHistoryPersistenceError`. Per ADR-033, a persistence failure
must never fail the originating prediction request: `persist()` still
raises on failure (so its own behavior is unambiguous and testable), but
its caller, `PredictionService._execute_history_stage`, is responsible
for catching `PredictionHistoryPersistenceError`, logging it, and
continuing to return a successful prediction response regardless.

`PredictionHistoryService` is wired into `PredictionService` as of Phase
5.2: once the RESPONSE stage completes, and only when
`PredictionOptions.save_history` is `true`, `PredictionService` calls
`prepare_history_record()` followed by `persist()`.

Phase 5.3 (History Retrieval, ADR-034) connects `list_history()` for
real: it delegates to `self._repository.list_by_user(user_id, limit,
offset)` -- ownership is enforced by the repository query itself, so
this method never needs to filter or verify results afterward. The
Prediction History Router (`app.api.v1.history.router`) calls
`list_history()` with an internal, non-configurable bound so every
authenticated user can retrieve their own full history, newest first,
without exposing pagination controls to API clients.

Phase 5.4 (History Pagination & Filtering, ADR-035) adds
`list_history_page()` alongside the existing `list_history()` -- rather
than changing `list_history()`'s signature or behavior -- so the
Phase 5.3 unfiltered/unbounded contract (and its existing test coverage)
remains untouched. `list_history_page()` is the method the Prediction
History Router (`app.api.v1.history.router`) now calls: it accepts an
already-validated `PredictionHistoryPageRequest`/`PredictionHistoryFilter`
pair (page/page size bounds and filter range consistency are validated
at construction time, ADR-035), coordinates two repository calls --
`list_by_user()` for the page of records and `count_by_user()` for the
total used to compute pagination metadata -- and returns a single
`PredictionHistoryPage` combining both.

Future phases extend this same class without changing its public
surface:
    - A future History Detail API wires `get_history()` (single-record
      retrieval, with ownership verification, still unimplemented) into
      a dedicated router endpoint.
"""

from app.core.logging import get_logger
from app.history.exceptions import PredictionHistoryPersistenceError
from app.history.filters import PredictionHistoryFilter
from app.history.mapper import PredictionHistoryMapper
from app.history.pagination import (
    PredictionHistoryPage,
    PredictionHistoryPageMetadata,
    PredictionHistoryPageRequest,
)
from app.history.prediction_history import PredictionHistory
from app.repositories.prediction_history_repository import PredictionHistoryRepository
from app.services.prediction_context import PredictionContext
from app.services.prediction_result import PredictionResult

logger = get_logger(__name__)


class PredictionHistoryService:
    """Orchestrates Prediction History preparation and (future) persistence.

    Depends only on a `PredictionHistoryRepository` implementation and a
    `PredictionHistoryMapper` -- both supplied through dependency
    injection, matching the constructor-injection convention already
    used by `PredictionService`, `RuntimeValidator`, and
    `RuntimeMetadataService`.
    """

    def __init__(
        self,
        repository: PredictionHistoryRepository,
        mapper: PredictionHistoryMapper | None = None,
    ) -> None:
        self._repository = repository
        self._mapper = mapper or PredictionHistoryMapper()

    def prepare_history_record(
        self,
        prediction_result: PredictionResult,
        context: PredictionContext,
    ) -> PredictionHistory:
        """Build (but do not persist) a `PredictionHistory` record.

        Delegates entirely to `PredictionHistoryMapper.to_history()`; this
        method performs no mapping logic of its own so the two layers
        cannot drift out of sync.

        Args:
            prediction_result: The service-layer outcome of
                `PredictionService.predict()` for a single request.
            context: The `PredictionContext` that originated
                `prediction_result`.

        Returns:
            An immutable `PredictionHistory`, ready for a future call to
            `persist()`. Never written to the repository by this method.

        Raises:
            InvalidHistoryInputError: If `prediction_result` or `context`
                is not an instance of the expected type (raised by the
                underlying mapper).
        """
        return self._mapper.to_history(prediction_result=prediction_result, context=context)

    async def persist(self, history: PredictionHistory) -> PredictionHistory:
        """Persist a prepared `PredictionHistory` record (Phase 5.2, ADR-033).

        Delegates to `self._repository.save(history)`. Any failure raised
        by the repository (database connectivity, constraint violation,
        etc.) is logged and re-raised as a `PredictionHistoryPersistenceError`
        -- never the raw underlying exception -- so callers never need to
        know which persistence backend is in use. Per ADR-033, this method
        never rolls back or otherwise affects the originating prediction
        request; it is the caller's (`PredictionService`'s) responsibility
        to catch `PredictionHistoryPersistenceError` and continue without
        failing the response.

        Args:
            history: An already-built `PredictionHistory`, typically from
                `prepare_history_record()`.

        Returns:
            The persisted `PredictionHistory`, unchanged from the input --
            persistence never mutates or recalculates any field.

        Raises:
            PredictionHistoryPersistenceError: If the record could not be
                persisted for any reason.
        """
        try:
            return await self._repository.save(history)
        except Exception as exc:
            logger.error(
                "Prediction history persistence failed: history_id=%s request_id=%s "
                "user_id=%s error=%s",
                history.history_id,
                history.request_id,
                history.user_id,
                exc,
            )
            raise PredictionHistoryPersistenceError() from exc

    async def get_history(self, history_id: str, user_id: str) -> PredictionHistory | None:
        """Retrieve a single history record owned by `user_id`.

        Not implemented in this phase. Reserved for a future single-record
        History Detail API, which will delegate to
        `self._repository.get_by_id(history_id, user_id)`.

        Raises:
            NotImplementedError: Always, in this phase.
        """
        raise NotImplementedError(
            "Single-record Prediction History retrieval is reserved for a "
            "future History Detail API; "
            "PredictionHistoryService.get_history() is not yet implemented."
        )

    async def list_history(
        self,
        user_id: str,
        limit: int,
        offset: int,
    ) -> list[PredictionHistory]:
        """Retrieve `user_id`'s prediction history, newest first (Phase 5.3, ADR-034).

        Delegates entirely to `self._repository.list_by_user(user_id,
        limit, offset)`; this method performs no querying, filtering, or
        ordering logic of its own so the two layers cannot drift out of
        sync. Ownership is enforced by the repository query itself
        (ADR-034) -- this method never receives, and therefore never needs
        to filter out, another user's records.

        Args:
            user_id: Identifier of the authenticated user whose history is
                being retrieved.
            limit: Maximum number of records to return. Supplied by the
                caller; Phase 5.3 callers pass an internal, non-configurable
                bound rather than a client-supplied value (pagination
                controls are not exposed until Phase 5.4).
            offset: Number of newest-first records to skip before
                collecting `limit` results.

        Returns:
            An immutable list of `PredictionHistory` domain objects owned
            by `user_id`, ordered newest first. Empty when the user has no
            history records.
        """
        logger.info(
            "Prediction history list retrieval started: user_id=%s limit=%d offset=%d",
            user_id,
            limit,
            offset,
        )

        records = await self._repository.list_by_user(
            user_id=user_id, limit=limit, offset=offset
        )

        logger.info(
            "Prediction history list retrieval completed: user_id=%s record_count=%d",
            user_id,
            len(records),
        )

        return records

    async def list_history_page(
        self,
        user_id: str,
        page_request: PredictionHistoryPageRequest,
        filters: PredictionHistoryFilter | None = None,
    ) -> PredictionHistoryPage:
        """Retrieve one validated, optionally filtered page of `user_id`'s history (Phase 5.4, ADR-035).

        Orchestrates pagination and filtering on top of the repository
        contract introduced in Phase 5.3 (ADR-034): it issues one
        `list_by_user()` call for this page's records and one
        `count_by_user()` call for the total matching record count, then
        derives `PredictionHistoryPageMetadata` from that total via
        `PredictionHistoryPageMetadata.from_totals()`. This method performs
        no pagination arithmetic of its own beyond delegating to that
        helper, and no filtering logic of its own -- `filters` is passed
        straight through to the repository, which is the only layer that
        turns it into SQL predicates.

        Ownership is enforced by the repository query itself for both
        calls, exactly as it already is for `list_history()` -- this
        method never receives, and therefore never needs to filter out,
        another user's records.

        Args:
            user_id: Identifier of the authenticated user whose history is
                being retrieved.
            page_request: An already-validated `PredictionHistoryPageRequest`
                (`page`/`page_size`, both range-checked at construction).
            filters: An already-validated `PredictionHistoryFilter`, or
                `None` to apply no filtering.

        Returns:
            A `PredictionHistoryPage` combining this page's
            `PredictionHistory` records (newest first) with pagination
            metadata describing the full, filtered result set.
        """
        logger.info(
            "Prediction history paginated retrieval started: user_id=%s page=%d "
            "page_size=%d filtered=%s",
            user_id,
            page_request.page,
            page_request.page_size,
            filters is not None and not filters.is_empty,
        )

        records = await self._repository.list_by_user(
            user_id=user_id,
            limit=page_request.limit,
            offset=page_request.offset,
            filters=filters,
        )
        total_records = await self._repository.count_by_user(user_id=user_id, filters=filters)

        metadata = PredictionHistoryPageMetadata.from_totals(
            page_request=page_request, total_records=total_records
        )

        logger.info(
            "Prediction history paginated retrieval completed: user_id=%s "
            "record_count=%d total_records=%d total_pages=%d",
            user_id,
            len(records),
            metadata.total_records,
            metadata.total_pages,
        )

        return PredictionHistoryPage(items=records, metadata=metadata)

