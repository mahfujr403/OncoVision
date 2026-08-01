"""JWT creation, decoding, and verification service.

Both access and refresh tokens are HS256-signed JWTs carrying a `type`
claim so that a refresh token can never be used where an access token is
expected, and vice versa.
"""

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import jwt
from jwt import ExpiredSignatureError
from jwt import InvalidTokenError as PyJWTInvalidTokenError

from app.core.exceptions import InvalidTokenError, TokenExpiredError
from app.core.settings import Settings, get_settings


class TokenType(str, Enum):
    """Distinguishes access tokens from refresh tokens within a JWT payload."""

    ACCESS = "access"
    REFRESH = "refresh"


class JWTService:
    """Creates and validates signed JSON Web Tokens."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def create_access_token(self, user_id: uuid.UUID, role: str) -> str:
        """Create a short-lived access token carrying the user's role."""
        return self._create_token(
            user_id=user_id,
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=self._settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            extra_claims={"role": role},
        )

    def create_refresh_token(self, user_id: uuid.UUID) -> str:
        """Create a long-lived refresh token."""
        return self._create_token(
            user_id=user_id,
            token_type=TokenType.REFRESH,
            expires_delta=timedelta(days=self._settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and verify the signature/expiry of a JWT.

        Raises:
            TokenExpiredError: If the token's expiry has passed.
            InvalidTokenError: If the token is malformed or the signature
                is invalid.
        """
        try:
            return jwt.decode(
                token,
                self._settings.JWT_SECRET_KEY,
                algorithms=[self._settings.JWT_ALGORITHM],
            )
        except ExpiredSignatureError as exc:
            raise TokenExpiredError() from exc
        except PyJWTInvalidTokenError as exc:
            raise InvalidTokenError() from exc

    def verify_token(self, token: str, expected_type: TokenType) -> dict[str, Any]:
        """Decode a token and ensure its `type` claim matches `expected_type`."""
        payload = self.decode_token(token)
        if payload.get("type") != expected_type.value:
            raise InvalidTokenError(message=f"Expected a {expected_type.value} token.")
        return payload

    def _create_token(
        self,
        user_id: uuid.UUID,
        token_type: TokenType,
        expires_delta: timedelta,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "type": token_type.value,
            "iat": now,
            "exp": now + expires_delta,
            "jti": str(uuid.uuid4()),
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, self._settings.JWT_SECRET_KEY, algorithm=self._settings.JWT_ALGORITHM)
