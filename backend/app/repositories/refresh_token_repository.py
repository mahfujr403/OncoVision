"""Data access layer for the `RefreshToken` model."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Encapsulates all database access for `RefreshToken` records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, refresh_token: RefreshToken) -> RefreshToken:
        """Persist a new `RefreshToken` and return it with generated fields loaded."""
        self._session.add(refresh_token)
        await self._session.flush()
        await self._session.refresh(refresh_token)
        return refresh_token

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Return a refresh token record by its hashed value, or `None`."""
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, refresh_token: RefreshToken) -> None:
        """Mark a single refresh token as revoked."""
        refresh_token.is_revoked = True
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Mark all active refresh tokens for a user as revoked."""
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True)
        )
