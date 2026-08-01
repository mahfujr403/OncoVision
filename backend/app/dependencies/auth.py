"""Reusable authentication and authorization dependencies.

Future protected endpoints should depend on `get_current_active_user`,
`require_admin`, or `require_roles` rather than reimplementing token
handling.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.dependencies.services import get_auth_service
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Paste the access token returned by /api/v1/auth/login.",
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve the authenticated user from a Bearer access token.

    Raises:
        UnauthorizedError: If no credentials were provided.
    """
    if credentials is None:
        raise UnauthorizedError(message="Authentication credentials were not provided.")
    return await auth_service.get_current_user(credentials.credentials)


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Resolve the current user, ensured active by `AuthService.get_current_user`."""
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable[..., Awaitable[User]]:
    """Build a dependency that only allows users with one of `allowed_roles`."""

    async def _require_roles(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError()
        return current_user

    return _require_roles


require_admin = require_roles(UserRole.ADMIN)
