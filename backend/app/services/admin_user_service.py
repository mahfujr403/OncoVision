"""Admin User Management Service (Phase 7.2/7.3, ADR-036).

`AdminUserService` is the single orchestration point for administrative
user-management operations, mirroring the role `PredictionHistoryService`
already plays for Prediction History. It depends only on the existing
`UserRepository` (Phase 7.2 extends it with additive, admin-facing
methods -- see `app.repositories.user_repository`) and the request-scoped
`AsyncSession` needed to commit those changes, exactly the same
constructor-injection shape already used by `AuthService`.

No user database logic is duplicated here: every method delegates
directly to `UserRepository`. This service's own responsibility is
strictly the administrative business rules layered on top -- translating
a missing user into `AdminUserNotFoundError`, and refusing operations
that would either lock out every administrator
(`LastAdministratorProtectionError`) or let an administrator
accidentally deactivate their own currently-authenticated account
(`SelfAccountStatusChangeError`).

Per ADR-036/ADR-037, administrators must never be able to manipulate
password hashes, JWT secrets, or other internal security configuration
directly -- this service exposes no method that touches
`User.password_hash`, and its dependency injection provider
(`app.dependencies.services.get_admin_user_service`) never wires in
`PasswordService` or `JWTService`.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.exceptions import (
    AdminUserNotFoundError,
    LastAdministratorProtectionError,
    SelfAccountStatusChangeError,
)
from app.core.logging import get_logger
from app.history.pagination import PredictionHistoryPageMetadata, PredictionHistoryPageRequest
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class AdminUserService:
    """Orchestrates administrative user listing, retrieval, and status management."""

    def __init__(self, session: AsyncSession, user_repository: UserRepository) -> None:
        self._session = session
        self._users = user_repository

    async def list_users(
        self, page_request: PredictionHistoryPageRequest
    ) -> tuple[list[User], PredictionHistoryPageMetadata]:
        """Return one page of registered users, newest first, with pagination metadata.

        Args:
            page_request: An already-validated `PredictionHistoryPageRequest`
                (`page`/`page_size`, both range-checked at construction).
                Reused as-is for user pagination -- its `page`/`page_size`
                arithmetic is not Prediction-History-specific.

        Returns:
            A tuple of the page's `User` records and the pagination
            metadata describing the full result set.
        """
        logger.info(
            "Admin user list retrieval started: page=%d page_size=%d",
            page_request.page,
            page_request.page_size,
        )

        users = await self._users.list_users(
            limit=page_request.limit, offset=page_request.offset
        )
        total_users = await self._users.count_users()
        metadata = PredictionHistoryPageMetadata.from_totals(
            page_request=page_request, total_records=total_users
        )

        logger.info(
            "Admin user list retrieval completed: record_count=%d total_records=%d",
            len(users),
            metadata.total_records,
        )

        return users, metadata

    async def get_user(self, user_id: str) -> User:
        """Retrieve a single user by ID.

        Raises:
            AdminUserNotFoundError: If `user_id` is not a well-formed UUID
                or does not match any registered user.
        """
        target = await self._resolve_user(user_id)
        return target

    async def activate_user(self, user_id: str) -> User:
        """Set the target user's `is_active` flag to `True`.

        Raises:
            AdminUserNotFoundError: If `user_id` does not match any
                registered user.
        """
        target = await self._resolve_user(user_id)

        target = await self._users.set_active_status(target, is_active=True)
        await self._session.commit()

        logger.info("Admin user activation completed: user_id=%s", user_id)
        return target

    async def deactivate_user(self, user_id: str, acting_user: User) -> User:
        """Set the target user's `is_active` flag to `False`.

        Args:
            user_id: Identifier of the user to deactivate.
            acting_user: The currently-authenticated administrator
                performing this action, used to enforce the
                self-deactivation and last-administrator safeguards
                below.

        Raises:
            AdminUserNotFoundError: If `user_id` does not match any
                registered user.
            SelfAccountStatusChangeError: If `user_id` matches
                `acting_user`'s own account.
            LastAdministratorProtectionError: If `user_id` is the last
                remaining active administrator account.
        """
        target = await self._resolve_user(user_id)

        if target.id == acting_user.id:
            raise SelfAccountStatusChangeError()

        if target.role == UserRole.ADMIN and target.is_active:
            active_admin_count = await self._users.count_by_role(
                UserRole.ADMIN, active_only=True
            )
            if active_admin_count <= 1:
                raise LastAdministratorProtectionError()

        target = await self._users.set_active_status(target, is_active=False)
        await self._session.commit()

        logger.info("Admin user deactivation completed: user_id=%s", user_id)
        return target

    async def _resolve_user(self, user_id: str) -> User:
        """Parse `user_id` and look it up, raising `AdminUserNotFoundError` on any miss."""
        try:
            parsed_id = uuid.UUID(user_id)
        except (ValueError, TypeError, AttributeError):
            logger.warning("Admin user lookup received a malformed user_id: %s", user_id)
            raise AdminUserNotFoundError() from None

        user = await self._users.get_by_id(parsed_id)
        if user is None:
            raise AdminUserNotFoundError()
        return user
