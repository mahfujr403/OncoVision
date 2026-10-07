"""Focused tests for `SecurityHeadersMiddleware` (Phase 6.1-C, ADR-043 / FINDING-08).

Verifies the HTTP security response header hardening:
1. Standard responses carry all required security headers.
2. Error responses (401, 403, 404, 422) maintain complete security headers.
3. Content-Security-Policy enforces strict API baseline ('none') without wildcards.
4. Documentation endpoints (/docs, /redoc) receive scoped, functional CSP.
5. Strict-Transport-Security (HSTS) behavior:
   - Safely omitted on plain HTTP development requests to protect localhost.
   - Enforced on production requests.
   - Enforced on HTTPS / X-Forwarded-Proto requests.
   - Fully respects configuration (max-age, includeSubDomains, preload, enabled).
6. Permissions-Policy restricts unused browser capabilities (camera, microphone, geolocation, payment).
7. Existing headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, X-XSS-Protection) are preserved.
8. Anti-regression test ensures no accidental wildcard or permissive policies.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.middleware.security_headers import (
    API_CONTENT_SECURITY_POLICY,
    DOCS_CONTENT_SECURITY_POLICY,
    PERMISSIONS_POLICY,
    _BASE_SECURITY_HEADERS,
)

HEALTH_PATH = "/api/v1/health"
NONEXISTENT_PATH = "/api/v1/nonexistent-endpoint-for-testing"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestStandardResponseSecurityHeaders:
    """Verify security headers on normal 200 OK responses."""

    def test_standard_response_contains_base_security_headers(self, client: TestClient) -> None:
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200

        for header_name, expected_value in _BASE_SECURITY_HEADERS.items():
            assert header_name in response.headers
            assert response.headers[header_name] == expected_value

    def test_standard_response_contains_api_csp(self, client: TestClient) -> None:
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
        assert response.headers["Content-Security-Policy"] == API_CONTENT_SECURITY_POLICY
        assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none';"

    def test_standard_response_contains_permissions_policy(self, client: TestClient) -> None:
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200
        assert "Permissions-Policy" in response.headers
        assert response.headers["Permissions-Policy"] == PERMISSIONS_POLICY
        assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=(), payment=()"

    def test_root_endpoint_contains_security_headers(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Content-Security-Policy"] == API_CONTENT_SECURITY_POLICY
        assert response.headers["Permissions-Policy"] == PERMISSIONS_POLICY


class TestErrorResponseSecurityHeaders:
    """Verify security headers remain consistently present on error responses."""

    def test_404_not_found_contains_all_security_headers(self, client: TestClient) -> None:
        response = client.get(NONEXISTENT_PATH)
        assert response.status_code == 404

        for header_name, expected_value in _BASE_SECURITY_HEADERS.items():
            assert response.headers.get(header_name) == expected_value

        assert response.headers.get("Content-Security-Policy") == API_CONTENT_SECURITY_POLICY
        assert response.headers.get("Permissions-Policy") == PERMISSIONS_POLICY

    def test_401_unauthorized_contains_all_security_headers(self, client: TestClient) -> None:
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

        for header_name, expected_value in _BASE_SECURITY_HEADERS.items():
            assert response.headers.get(header_name) == expected_value

        assert response.headers.get("Content-Security-Policy") == API_CONTENT_SECURITY_POLICY
        assert response.headers.get("Permissions-Policy") == PERMISSIONS_POLICY

    def test_422_validation_error_contains_all_security_headers(self, client: TestClient) -> None:
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

        for header_name, expected_value in _BASE_SECURITY_HEADERS.items():
            assert response.headers.get(header_name) == expected_value

        assert response.headers.get("Content-Security-Policy") == API_CONTENT_SECURITY_POLICY
        assert response.headers.get("Permissions-Policy") == PERMISSIONS_POLICY


class TestContentSecurityPolicyDirectives:
    """Verify CSP directives and anti-permissiveness rules."""

    def test_api_csp_has_no_wildcards(self, client: TestClient) -> None:
        response = client.get(HEALTH_PATH)
        csp = response.headers.get("Content-Security-Policy", "")

        assert "*" not in csp
        assert "default-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_api_csp_has_no_unsafe_directives(self, client: TestClient) -> None:
        response = client.get(HEALTH_PATH)
        csp = response.headers.get("Content-Security-Policy", "")

        assert "unsafe-inline" not in csp
        assert "unsafe-eval" not in csp

    def test_docs_endpoints_receive_functional_documentation_csp(self, client: TestClient) -> None:
        for docs_path in ("/docs", "/redoc"):
            response = client.get(docs_path)
            assert response.status_code == 200
            csp = response.headers.get("Content-Security-Policy", "")
            assert csp == DOCS_CONTENT_SECURITY_POLICY
            assert "https://cdn.jsdelivr.net" in csp
            assert "frame-ancestors 'none'" in csp


class TestStrictTransportSecurityBehavior:
    """Verify HSTS behavior across environments and protocol schemes."""

    def test_development_plain_http_omits_hsts(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """Plain HTTP in development must never receive HSTS to avoid locking localhost."""
        monkeypatch.setattr(settings, "APP_ENV", "development")
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers

    def test_production_environment_includes_hsts(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """Production responses must enforce strong HSTS."""
        monkeypatch.setattr(settings, "APP_ENV", "production")
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    def test_development_https_forwarded_proto_includes_hsts(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """Requests terminating TLS at a reverse proxy (X-Forwarded-Proto) receive HSTS."""
        monkeypatch.setattr(settings, "APP_ENV", "development")
        response = client.get(HEALTH_PATH, headers={"x-forwarded-proto": "https"})
        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    def test_hsts_disabled_via_settings(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """When HSTS_ENABLED is False, HSTS header is omitted even in production."""
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setattr(settings, "HSTS_ENABLED", False)
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers

    def test_hsts_custom_configuration(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        """HSTS max-age and optional preload flag reflect Settings configuration."""
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setattr(settings, "HSTS_MAX_AGE_SECONDS", 63072000)
        monkeypatch.setattr(settings, "HSTS_PRELOAD", True)
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200
        assert response.headers["Strict-Transport-Security"] == "max-age=63072000; includeSubDomains; preload"


class TestAntiRegressionAndExistingHeadersPreservation:
    """Verify existing headers and guard against loosening security controls."""

    def test_all_expected_headers_coexist_in_single_response(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "APP_ENV", "production")
        response = client.get(HEALTH_PATH)
        assert response.status_code == 200

        # Verify all 7 headers exist simultaneously
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=(), payment=()"
        assert response.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none';"
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    def test_rejection_of_permissive_wildcards_in_csp(self) -> None:
        """Ensure API CSP constant never contains wildcards."""
        assert "*" not in API_CONTENT_SECURITY_POLICY
        assert "script-src *" not in API_CONTENT_SECURITY_POLICY
        assert "style-src *" not in API_CONTENT_SECURITY_POLICY
