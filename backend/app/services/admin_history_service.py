"""Admin Prediction/History Oversight Service (Phase 7.4, ADR-036).

`AdminHistoryService` is a thin orchestration layer over the existing
`PredictionHistoryService` -- per ADR-036/the Phase 7.4 scope, this is
explicitly NOT a second Prediction History implementation. It exists only
so the Admin History Router depends on an Admin-named service (matching
the Router -> Service -> Repository/Existing Service architecture laid
out in ADR-036) without importing `PredictionHistoryService` directly
into `app.api.v1.admin`, keeping the same one-service-per-router-module
convention already used elsewhere (`ReportService`, `PredictionAnalyticsService`).

Every method here delegates directly to `PredictionHistoryService`'s own
Phase 7.4 admin methods (`list_history_admin()` / `get_history_admin()`)
-- no filtering, pagination, or lookup logic is duplicated. Prediction
History remains immutable and append-only: no method on this service (or
on `PredictionHistoryService`) ever modifies a record.
"""

import uuid

from app.core.logging import get_logger
from app.history.filters import PredictionHistoryFilter
from app.history.pagination import PredictionHistoryPage, PredictionHistoryPageRequest
from app.history.prediction_history import PredictionHistory
from app.repositories.user_repository import UserRepository
from app.services.prediction_history_service import PredictionHistoryService

logger = get_logger(__name__)

_UNKNOWN_OWNER_EMAIL = "Unknown"


class AdminHistoryService:
    """Orchestrates administrative prediction history oversight."""

    def __init__(
        self,
        history_service: PredictionHistoryService,
        user_repository: UserRepository | None = None,
    ) -> None:
        self._history_service = history_service
        self._users = user_repository

    async def list_history(
        self,
        page_request: PredictionHistoryPageRequest,
        filters: PredictionHistoryFilter | None = None,
        user_id: str | None = None,
    ) -> PredictionHistoryPage:
        """Return one page of prediction history across every user (or one, via `user_id`).

        Delegates entirely to `PredictionHistoryService.list_history_admin()`.
        """
        return await self._history_service.list_history_admin(
            page_request=page_request, filters=filters, user_id=user_id
        )

    async def get_history(self, history_id: str) -> PredictionHistory | None:
        """Return a single prediction history record by ID, regardless of owner.

        Delegates entirely to `PredictionHistoryService.get_history_admin()`.
        """
        return await self._history_service.get_history_admin(history_id=history_id)

    async def get_user_email(self, user_id: str) -> str:
        """Resolve a single history record owner's email address.

        Additive Phase 7.4 helper: administrators see the owner's email
        alongside `user_id` on the history detail view. Returns
        `"Unknown"` -- never raises -- when no `UserRepository` was
        injected, `user_id` is not a well-formed UUID, or no user record
        matches it, since a missing owner email must never block viewing
        an otherwise-valid history record.
        """
        emails = await self.get_user_emails([user_id])
        return emails.get(user_id, _UNKNOWN_OWNER_EMAIL)

    async def get_user_emails(self, user_ids: list[str]) -> dict[str, str]:
        """Batch-resolve owner emails for a page of history records.

        Additive Phase 7.4 helper: issues a single `UserRepository.get_by_ids()`
        query for every distinct `user_id` rather than one lookup per
        record. Malformed IDs are skipped rather than raised, and IDs with
        no matching user are simply absent from the returned mapping --
        callers fall back to `"Unknown"` for those.
        """
        if self._users is None or not user_ids:
            return {}

        parsed_ids: dict[str, uuid.UUID] = {}
        for user_id in set(user_ids):
            try:
                parsed_ids[user_id] = uuid.UUID(user_id)
            except (ValueError, TypeError, AttributeError):
                logger.warning("Admin history owner lookup received a malformed user_id: %s", user_id)

        if not parsed_ids:
            return {}

        users = await self._users.get_by_ids(list(parsed_ids.values()))
        email_by_uuid = {user.id: user.email for user in users}

        return {
            user_id: email_by_uuid[parsed]
            for user_id, parsed in parsed_ids.items()
            if parsed in email_by_uuid
        }
