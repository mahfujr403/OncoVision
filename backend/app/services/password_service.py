"""Password hashing and verification service.

Uses Passlib's bcrypt scheme. Passwords are never stored or logged in
plaintext anywhere in the application.
"""

from passlib.context import CryptContext

from app.core.settings import Settings, get_settings


class PasswordService:
    """Hashes and verifies user passwords using bcrypt."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=self._settings.BCRYPT_ROUNDS,
        )

    def hash_password(self, plain_password: str) -> str:
        """Return a bcrypt hash of a plaintext password."""
        return self._context.hash(plain_password)

    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        """Return `True` if `plain_password` matches the given bcrypt hash."""
        return self._context.verify(plain_password, password_hash)
