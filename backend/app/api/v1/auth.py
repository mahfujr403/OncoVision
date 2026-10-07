"""Authentication endpoints.

Routers only receive requests and delegate to services; no business logic
lives here.

Phase 6.1-D: Authentication Rate Limiting (ADR-044 / FINDING-05)
Enforces in-memory sliding window rate limits on /login and /register before
expensive cryptographic and database operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.constants.app import TAG_AUTH
from app.core.config import settings
from app.dependencies.auth import get_current_active_user
from app.dependencies.services import get_auth_service
from app.llm.rate_limiter import RateLimiter
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.utils.response import success_response

router = APIRouter(prefix="/auth", tags=[TAG_AUTH])

# Dedicated, independent sliding window rate limiters (Phase 6.1-D)
_login_rate_limiter = RateLimiter()
_register_rate_limiter = RateLimiter()


def _extract_client_ip(request: Request) -> str:
    """Extract client IP address reliably, preferring X-Forwarded-For when behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _client_context(request: Request) -> dict[str, str | None]:
    """Extract device name, IP address, and user agent from a request."""
    return {
        "device_name": request.headers.get("X-Device-Name"),
        "ip_address": _extract_client_ip(request),
        "user_agent": request.headers.get("User-Agent"),
    }


def _access_token_expires_in() -> int:
    """Return the access token lifetime in seconds."""
    return settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with the USER role.",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """Register a new user account."""
    client_ip = _extract_client_ip(request)
    normalized_email = payload.email.strip().lower()

    # Rate limiting enforcement (in-memory sliding window)
    ip_key = f"register:ip:{client_ip}"
    email_key = f"register:email:{normalized_email}"

    ip_remaining = _register_rate_limiter.get_remaining(
        ip_key,
        max_requests=settings.AUTH_REGISTER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
    )
    email_remaining = _register_rate_limiter.get_remaining(
        email_key,
        max_requests=settings.AUTH_REGISTER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
    )

    if ip_remaining <= 0 or email_remaining <= 0:
        retry_after = max(
            _register_rate_limiter.get_retry_after(ip_key, settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS),
            _register_rate_limiter.get_retry_after(email_key, settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS),
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    await _register_rate_limiter.check_rate_limit(
        ip_key,
        max_requests=settings.AUTH_REGISTER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
    )
    await _register_rate_limiter.check_rate_limit(
        email_key,
        max_requests=settings.AUTH_REGISTER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
    )

    user = await auth_service.register(payload)
    response_data = RegisterResponse(user=UserResponse.model_validate(user))
    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Registration successful.",
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/login", summary="Authenticate and receive tokens")
async def login(
    payload: LoginRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """Authenticate a user and issue an access/refresh token pair."""
    client_ip = _extract_client_ip(request)
    normalized_email = payload.email.strip().lower()

    # Rate limiting enforcement (in-memory sliding window)
    # Checks both IP-level and account-level to prevent single-dimension bypass
    ip_key = f"ip:{client_ip}"
    pair_key = f"pair:{client_ip}:{normalized_email}"

    ip_remaining = _login_rate_limiter.get_remaining(
        ip_key,
        max_requests=settings.AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    pair_remaining = _login_rate_limiter.get_remaining(
        pair_key,
        max_requests=settings.AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )

    if ip_remaining <= 0 or pair_remaining <= 0:
        retry_after = max(
            _login_rate_limiter.get_retry_after(ip_key, settings.AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS),
            _login_rate_limiter.get_retry_after(pair_key, settings.AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS),
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    await _login_rate_limiter.check_rate_limit(
        ip_key,
        max_requests=settings.AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    await _login_rate_limiter.check_rate_limit(
        pair_key,
        max_requests=settings.AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    )

    context = _client_context(request)
    user, access_token, refresh_token = await auth_service.login(
        email=payload.email,
        password=payload.password,
        **context,
    )
    response_data = LoginResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=_access_token_expires_in(),
    )
    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Login successful.",
    )


@router.post("/refresh", summary="Exchange a refresh token for a new token pair")
async def refresh(
    payload: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """Rotate a valid refresh token for a new access/refresh token pair."""
    access_token, refresh_token = await auth_service.refresh(payload.refresh_token)
    response_data = RefreshResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=_access_token_expires_in(),
    )
    return success_response(
        data=response_data.model_dump(mode="json"),
        message="Token refreshed successfully.",
    )


@router.post("/logout", summary="Revoke a single refresh token")
async def logout(
    payload: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """Log out of a single device/session by revoking its refresh token."""
    await auth_service.logout(payload.refresh_token)
    return success_response(message="Logout successful.")


@router.post("/logout-all", summary="Revoke all refresh tokens for the current user")
async def logout_all(
    current_user: Annotated[User, Depends(get_current_active_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """Log out of all devices by revoking every active refresh token."""
    await auth_service.logout_all_devices(current_user.id)
    return success_response(message="Logged out from all devices successfully.")


@router.get("/me", summary="Get the currently authenticated user")
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Return the profile of the currently authenticated user."""
    return success_response(
        data={"user": UserResponse.model_validate(current_user).model_dump(mode="json")},
        message="Current user retrieved successfully.",
    )
