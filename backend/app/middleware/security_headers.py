"""Middleware that attaches standard security headers to every response.

Phase 6.1-C: Security Headers Hardening (ADR-043 / FINDING-08)
Enforces modern defense-in-depth security response headers:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Referrer-Policy: strict-origin-when-cross-origin
- X-XSS-Protection: 1; mode=block
- Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
- Content-Security-Policy:
    - API endpoints: default-src 'none'; frame-ancestors 'none';
    - Documentation endpoints (/docs, /redoc): restrictive policy scoped strictly
      to required Swagger UI / ReDoc CDN assets (jsdelivr) and inline initializers.
- Strict-Transport-Security:
    - Enforced in production or on HTTPS connections (max-age=31536000; includeSubDomains)
    - Omitted on plain HTTP development responses to avoid breaking localhost.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

# Base hardening headers applied to all responses
_BASE_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-XSS-Protection": "1; mode=block",
}

# Compatibility alias
_SECURITY_HEADERS = _BASE_SECURITY_HEADERS

# Permissions-Policy restricting unused browser APIs on the backend
PERMISSIONS_POLICY: str = "camera=(), microphone=(), geolocation=(), payment=()"

# Strict Content-Security-Policy for API endpoints (FINDING-08)
API_CONTENT_SECURITY_POLICY: str = "default-src 'none'; frame-ancestors 'none';"

# Scoped Content-Security-Policy for interactive Swagger/OpenAPI documentation
# Needed because FastAPI /docs and /redoc render HTML embedding CDN assets and inline bootstrap scripts
DOCS_CONTENT_SECURITY_POLICY: str = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' https://fastapi.tiangolo.com data:; "
    "frame-ancestors 'none';"
)

_DOCS_PATHS: frozenset[str] = frozenset({
    "/docs",
    "/redoc",
    "/docs/oauth2-redirect",
})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach standard hardening headers to every outgoing response."""

    def _should_apply_hsts(self, request: Request) -> bool:
        """Determine whether Strict-Transport-Security should be attached.

        HSTS is strictly avoided on plain HTTP localhost development to prevent
        locking developers out of non-TLS local development. It is enabled:
        - When running in production (APP_ENV=production)
        - When the request protocol is HTTPS (direct scheme or X-Forwarded-Proto)
        """
        if not settings.HSTS_ENABLED:
            return False

        is_https = (
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto", "").lower() == "https"
        )

        if settings.is_production:
            return True

        return is_https

    def _apply_security_headers(self, request: Request, response: Response) -> None:
        """Inject all required security headers into response headers."""
        # 1. Base security headers (preserved from initial baseline)
        for header_name, header_value in _BASE_SECURITY_HEADERS.items():
            response.headers[header_name] = header_value

        # 2. Permissions-Policy
        response.headers["Permissions-Policy"] = PERMISSIONS_POLICY

        # 3. Content-Security-Policy
        if request.url.path in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = DOCS_CONTENT_SECURITY_POLICY
        else:
            response.headers["Content-Security-Policy"] = API_CONTENT_SECURITY_POLICY

        # 4. Strict-Transport-Security
        if self._should_apply_hsts(request):
            response.headers["Strict-Transport-Security"] = settings.hsts_header_value

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        self._apply_security_headers(request, response)
        return response
