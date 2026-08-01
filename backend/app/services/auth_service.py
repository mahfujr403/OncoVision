"""Authentication business logic.

Coordinates repositories, password hashing, and JWT issuance to implement
registration, login, token refresh, and logout use cases. Routers never
touch repositories or JWT/password internals directly.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.core.settings import Settings, get_settings
from app.models.enums import UserRole
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest
from app.services.jwt_service import JWTService, TokenType
from app.services.password_service import PasswordService
from app.utils.security import hash_token


class AuthService:
    """Implements the register / login / refresh / logout use cases."""

    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        password_service: PasswordService,
        jwt_service: JWTService,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository
        self._passwords = password_service
        self._jwt = jwt_service
        self._settings = settings or get_settings()

    async def register(self, payload: RegisterRequest) -> User:
        """Create a new user account.

        Raises:
            DuplicateEmailError: If an account with the given email already exists.
        """
        existing_user = await self._users.get_by_email(payload.email)
        if existing_user is not None:
            raise DuplicateEmailError()

        user = User(
            full_name=payload.full_name,
            email=payload.email,
            password_hash=self._passwords.hash_password(payload.password),
            role=UserRole.USER,
        )
        user = await self._users.create(user)
        await self._session.commit()
        return user

    async def login(
        self,
        email: str,
        password: str,
        device_name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        """Authenticate a user and issue a new access/refresh token pair.

        Raises:
            InvalidCredentialsError: If the email or password is incorrect.
            InactiveUserError: If the account has been deactivated.
        """
        user = await self._users.get_by_email(email)
        if user is None or not self._passwords.verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()

        user = await self._users.update_last_login(user)
        access_token, refresh_token = await self._issue_token_pair(
            user, device_name=device_name, ip_address=ip_address, user_agent=user_agent
        )
        await self._session.commit()
        return user, access_token, refresh_token

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Exchange a valid, unrevoked refresh token for a new token pair.

        The presented refresh token is revoked as part of rotation.

        Raises:
            InvalidTokenError: If the token is malformed, unknown, expired, or revoked.
            InactiveUserError: If the owning account has been deactivated.
        """
        payload = self._jwt.verify_token(refresh_token, TokenType.REFRESH)
        token_hash = hash_token(refresh_token)
        stored_token = await self._refresh_tokens.get_by_token_hash(token_hash)

        if stored_token is None or stored_token.is_revoked:
            raise InvalidTokenError(message="Refresh token has been revoked or does not exist.")
        if stored_token.expires_at < datetime.now(timezone.utc):
            raise InvalidTokenError(message="Refresh token has expired.")

        user = await self._users.get_by_id(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise InactiveUserError()

        await self._refresh_tokens.revoke(stored_token)
        access_token, new_refresh_token = await self._issue_token_pair(
            user,
            device_name=stored_token.device_name,
            ip_address=stored_token.ip_address,
            user_agent=stored_token.user_agent,
        )
        await self._session.commit()
        return access_token, new_refresh_token

    async def logout(self, refresh_token: str) -> None:
        """Revoke a single refresh token, logging out one device/session."""
        token_hash = hash_token(refresh_token)
        stored_token = await self._refresh_tokens.get_by_token_hash(token_hash)
        if stored_token is not None and not stored_token.is_revoked:
            await self._refresh_tokens.revoke(stored_token)
            await self._session.commit()

    async def logout_all_devices(self, user_id: uuid.UUID) -> None:
        """Revoke all active refresh tokens belonging to a user."""
        await self._refresh_tokens.revoke_all_for_user(user_id)
        await self._session.commit()

    async def get_current_user(self, access_token: str) -> User:
        """Resolve the authenticated `User` for a valid access token.

        Raises:
            InvalidTokenError: If the token is malformed or the user no longer exists.
            InactiveUserError: If the account has been deactivated.
        """
        payload = self._jwt.verify_token(access_token, TokenType.ACCESS)
        user = await self._users.get_by_id(uuid.UUID(payload["sub"]))
        if user is None:
            raise InvalidTokenError(message="User associated with this token no longer exists.")
        if not user.is_active:
            raise InactiveUserError()
        return user

    async def _issue_token_pair(
        self,
        user: User,
        device_name: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[str, str]:
        """Create a new access/refresh token pair and persist the hashed refresh token."""
        access_token = self._jwt.create_access_token(user_id=user.id, role=user.role.value)
        refresh_token = self._jwt.create_refresh_token(user_id=user.id)

        refresh_token_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=self._settings.REFRESH_TOKEN_EXPIRE_DAYS),
            device_name=device_name,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._refresh_tokens.create(refresh_token_record)
        return access_token, refresh_token
