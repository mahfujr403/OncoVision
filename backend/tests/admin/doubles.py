"""Shared test doubles for the Phase 7 Administration & Governance test suite.

`FakeUserRepository` and `FakeSession` duck-type the same method surface
`app.repositories.user_repository.UserRepository` exposes to
`AdminUserService` (`get_by_id`, `list_users`, `count_users`,
`count_by_role`, `set_active_status`) plus the `AsyncSession.commit()`
call `AdminUserService` makes directly -- letting `AdminUserService` be
unit-tested without a real database, mirroring how
`tests/history/test_prediction_history_repository.py`'s
`InMemoryPredictionHistoryRepository` lets `PredictionHistoryService` be
unit-tested without one.
"""

import uuid
from datetime import datetime, timezone

from app.history.filters import PredictionHistoryFilter
from app.history.prediction_history import PredictionHistory
from app.models.enums import UserRole
from app.models.refresh_token import RefreshToken  # noqa: F401 -- registers the ORM
# relationship `User.refresh_tokens` targets, matching the reasoning
# documented on `app.models.user.User.refresh_tokens`. Constructing a bare
# `User()` without this import first raises `InvalidRequestError` because
# SQLAlchemy's declarative mapper configuration can't resolve the
# string-based `"RefreshToken"` relationship target.
from app.models.user import User
from app.repositories.prediction_history_repository import PredictionHistoryRepository


def make_user(
    *,
    role: UserRole = UserRole.USER,
    is_active: bool = True,
    email: str = "user@example.com",
    full_name: str = "Test User",
    user_id: uuid.UUID | None = None,
) -> User:
    """Build a minimal, unsaved `User` instance for tests."""
    return User(
        id=user_id or uuid.uuid4(),
        full_name=full_name,
        email=email,
        password_hash="not-a-real-hash",
        role=role,
        is_active=is_active,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class FakeSession:
    """Duck-types the one `AsyncSession` method `AdminUserService` calls directly."""

    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class FakeUserRepository:
    """In-memory double of `UserRepository`'s Phase 7.2/7.3 admin-facing surface."""

    def __init__(self, users: list[User]) -> None:
        self._users: dict[uuid.UUID, User] = {user.id: user for user in users}

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._users.get(user_id)

    async def get_by_ids(self, user_ids: list[uuid.UUID]) -> list[User]:
        return [self._users[uid] for uid in user_ids if uid in self._users]

    async def list_users(self, limit: int, offset: int) -> list[User]:
        ordered = sorted(self._users.values(), key=lambda u: u.created_at, reverse=True)
        return ordered[offset : offset + limit]

    async def count_users(self) -> int:
        return len(self._users)

    async def count_by_role(self, role: UserRole, active_only: bool = False) -> int:
        matches = [u for u in self._users.values() if u.role == role]
        if active_only:
            matches = [u for u in matches if u.is_active]
        return len(matches)

    async def set_active_status(self, user: User, is_active: bool) -> User:
        user.is_active = is_active
        self._users[user.id] = user
        return user


class AdminAwarePredictionHistoryRepository(PredictionHistoryRepository):
    """In-memory `PredictionHistoryRepository` double implementing the Phase 7.4 admin methods.

    Every pre-Phase-7 double under `tests/history` and `tests/reports`
    predates `list_all()`/`count_all()`/`get_by_id_unscoped()` and
    intentionally does not implement them (those methods default to
    `NotImplementedError` on the ABC precisely so those doubles need no
    changes). This double exists specifically so `AdminHistoryService`
    (and, transitively, `PredictionHistoryService.list_history_admin()`/
    `get_history_admin()`) can be exercised without a real database.
    """

    def __init__(self, records: list[PredictionHistory] | None = None) -> None:
        self._records: list[PredictionHistory] = list(records or [])

    async def save(self, history: PredictionHistory) -> PredictionHistory:
        self._records.append(history)
        return history

    async def get_by_id(self, history_id: str, user_id: str) -> PredictionHistory | None:
        for record in self._records:
            if record.history_id == history_id and record.user_id == user_id:
                return record
        return None

    async def list_by_user(
        self,
        user_id: str,
        limit: int,
        offset: int,
        filters: PredictionHistoryFilter | None = None,
    ) -> list[PredictionHistory]:
        matching = [record for record in self._records if record.user_id == user_id]
        return matching[offset : offset + limit]

    async def count_by_user(
        self, user_id: str, filters: PredictionHistoryFilter | None = None
    ) -> int:
        return len([record for record in self._records if record.user_id == user_id])

    async def list_all(
        self,
        limit: int,
        offset: int,
        filters: PredictionHistoryFilter | None = None,
        user_id: str | None = None,
    ) -> list[PredictionHistory]:
        matching = self._records
        if user_id is not None:
            matching = [record for record in matching if record.user_id == user_id]
        if filters is not None and filters.status is not None:
            matching = [record for record in matching if record.status == filters.status]
        return matching[offset : offset + limit]

    async def count_all(
        self,
        filters: PredictionHistoryFilter | None = None,
        user_id: str | None = None,
    ) -> int:
        return len(
            await self.list_all(limit=len(self._records) or 1, offset=0, filters=filters, user_id=user_id)
        )

    async def get_by_id_unscoped(self, history_id: str) -> PredictionHistory | None:
        for record in self._records:
            if record.history_id == history_id:
                return record
        return None
