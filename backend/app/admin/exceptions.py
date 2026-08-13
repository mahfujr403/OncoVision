"""Administration & Governance exceptions (Phase 7, ADR-036).

Extend the application's centralized `OncoVisionError` so they are
automatically handled by the existing global exception handlers
(`app.core.exceptions.register_exception_handlers`) and never leak
internal details to API clients -- mirroring the same convention already
used by `app.history.exceptions` and `app.ml.ensemble.exceptions`.

`AdminError` is the shared base for every exception raised by the
`app.admin`/`app.services.admin_*` packages, letting callers catch the
whole hierarchy with a single `except AdminError:` when they don't need
to distinguish the specific failure.
"""

from fastapi import status

from app.core.exceptions import OncoVisionError


class AdminError(OncoVisionError):
    """Base exception for every error raised by the Administration package."""


class AdminUserNotFoundError(AdminError):
    """Raised when an administrative operation targets a nonexistent user."""

    def __init__(self, message: str = "The requested user was not found.") -> None:
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND)


class LastAdministratorProtectionError(AdminError):
    """Raised when an operation would leave the system with zero administrators.

    Guards against an administrator deactivating (or otherwise disabling)
    the last remaining `UserRole.ADMIN` account, which would permanently
    lock every administrator out of the Administration layer (ADR-036,
    Phase 7.3's "Prevent unsafe behavior" requirement).
    """

    def __init__(
        self,
        message: str = (
            "This action would leave the system with no active administrator "
            "accounts and has been blocked."
        ),
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT)


class SelfAccountStatusChangeError(AdminError):
    """Raised when an administrator attempts to deactivate their own account.

    An administrator locking out their own currently-authenticated
    session is very likely an accident, and -- combined with
    `LastAdministratorProtectionError` -- is otherwise indistinguishable
    from a legitimate action, so it is rejected outright rather than
    silently permitted (Phase 7.3's "self-management edge cases" test
    requirement).
    """

    def __init__(
        self, message: str = "Administrators cannot deactivate their own account."
    ) -> None:
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST)
