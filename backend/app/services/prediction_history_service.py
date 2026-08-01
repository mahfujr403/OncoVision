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

Future phases extend this same class without changing its public
surface:
    - Phase 5.3: adds `get_history()` (single-record retrieval, with
      ownership verification).
    - Phase 5.4: adds pagination and filtering on top of `list_history()`.
    - Phase 5.5: History Detail API wires this service into a dedicated
      router.
"""

from app.core.logging import get_logger
from app.history.exceptions import PredictionHistoryPersistenceError
from app.history.mapper import PredictionHistoryMapper
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

        Not implemented in this phase. Reserved for Phase 5.3 (History
        Retrieval), which will delegate to
        `self._repository.get_by_id(history_id, user_id)`.

        Raises:
            NotImplementedError: Always, in this phase.
        """
        raise NotImplementedError(
            "Prediction History retrieval begins in Phase 5.3; "
            "PredictionHistoryService.get_history() is not yet implemented."
        )

    async def list_history(
        self,
        user_id: str,
        limit: int,
        offset: int,
    ) -> list[PredictionHistory]:
        """Retrieve a page of history records owned by `user_id`.

        Not implemented in this phase. Reserved for Phase 5.4 (History
        Pagination & Filtering), which will delegate to
        `self._repository.list_by_user(user_id, limit, offset)`.

        Raises:
            NotImplementedError: Always, in this phase.
        """
        raise NotImplementedError(
            "Prediction History pagination begins in Phase 5.4; "
            "PredictionHistoryService.list_history() is not yet implemented."
        )

