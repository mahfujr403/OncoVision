"""Data access layer for the `User` model.

Repositories only perform database access. Business rules (duplicate email
checks, password verification, etc.) belong in the service layer.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
