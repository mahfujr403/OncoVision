"""Data access layer for the `User` model.

Repositories only perform database access. Business rules (duplicate email
checks, password verification, etc.) belong in the service layer.

Phase 7.2/7.3 (Administration & Governance, ADR-036) extend this
repository with additive, admin-facing read/write methods --
`list_users()`, `count_users()`, `count_by_role()`, and
`set_active_status()`. Every pre-existing method above is left untouched;
these new methods follow the exact same constructor-injection and
flush/refresh conventions already established by `create()` and
`update_last_login()`.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import User


class UserRepository:
    """Encapsulates all database access for `User` records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return a user by primary key, or `None` if not found."""
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by email address, or `None` if not found."""
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Persist a new `User` and return it with database-generated fields loaded."""
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def update_last_login(self, user: User) -> User:
        """Set `last_login` to the current UTC time and persist the change."""
        user.last_login = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def list_users(self, limit: int, offset: int) -> list[User]:
        """Return one page of users, newest first (Phase 7.2, ADR-036).

        Mirrors the pagination shape already used by
        `PredictionHistoryRepository.list_by_user()` -- ordered,
        `limit`/`offset`-bounded, and read-only.
        """
        result = await self._session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_users(self) -> int:
        """Return the total number of registered users (Phase 7.2, ADR-036)."""
        result = await self._session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def count_by_role(self, role: UserRole, active_only: bool = False) -> int:
        """Return the total number of users with `role` (Phase 7.3, ADR-036).

        Used by `AdminUserService` to guard against deactivating the last
        remaining active administrator account. `active_only=True`
        restricts the count to users with `is_active=True`, since an
        already-deactivated administrator does not count as an available
        administrator.
        """
        statement = select(func.count(User.id)).where(User.role == role)
        if active_only:
            statement = statement.where(User.is_active.is_(True))
        result = await self._session.execute(statement)
        return result.scalar_one()

    async def set_active_status(self, user: User, is_active: bool) -> User:
        """Set `is_active` on `user` and persist the change (Phase 7.3, ADR-036).

        Reuses the existing `is_active` column (ADR-036: "If the project
        already contains `is_active`, use it") -- no new account-status
        field is introduced.
        """
        user.is_active = is_active
        await self._session.flush()
        await self._session.refresh(user)
        return user
