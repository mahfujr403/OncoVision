"""Focused security tests for CORS configuration and middleware hardening (Phase 6.1-B).

Verifies:
1. Canonical production origin (https://oncovision-live.netlify.app) receives expected CORS headers.
2. Malicious Netlify subdomains (e.g. https://malicious-phish.netlify.app) are rejected.
3. Arbitrary external origins (e.g. https://attacker-site.com) are rejected.
4. Wildcard origins ('*') are strictly rejected in production when credentials are enabled.
5. Localhost development origins remain functional in non-production environments.
6. Access-Control-Allow-Credentials is true for allowed origins.
7. OPTIONS preflight behavior for trusted, malicious, and development origins.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.settings import Settings
from app.main import app

CANONICAL_PROD_ORIGIN = "https://oncovision-live.netlify.app"
MALICIOUS_NETLIFY_ORIGIN = "https://malicious-phish.netlify.app"
ATTACKER_ORIGIN = "https://attacker-domain.org"
DEV_LOCALHOST_ORIGIN = "http://localhost:5173"
DEV_127_ORIGIN = "http://127.0.0.1:3000"


@pytest.fixture
def client():
    return TestClient(app)


class TestCORSSecurityHardening:
    """End-to-end CORS enforcement on the FastAPI application."""

    def test_canonical_production_origin_allowed(self, client: TestClient) -> None:
        """The verified production frontend receives authorization and credentials."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": CANONICAL_PROD_ORIGIN},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == CANONICAL_PROD_ORIGIN
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_malicious_netlify_origin_rejected(self, client: TestClient) -> None:
        """Arbitrary *.netlify.app origins must never receive CORS authorization."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": MALICIOUS_NETLIFY_ORIGIN},
        )
        assert response.status_code == 200
        # The CORS middleware MUST omit access-control-allow-origin for rejected origins
        assert "access-control-allow-origin" not in response.headers

    def test_arbitrary_untrusted_origin_rejected(self, client: TestClient) -> None:
        """Arbitrary third-party origins must never receive CORS authorization."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": ATTACKER_ORIGIN},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

    def test_localhost_development_origin_allowed(self, client: TestClient) -> None:
        """Intended localhost development ports remain functional."""
        response = client.get(
            "/api/v1/health",
            headers={"Origin": DEV_LOCALHOST_ORIGIN},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == DEV_LOCALHOST_ORIGIN
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_preflight_options_for_canonical_origin(self, client: TestClient) -> None:
        """Preflight OPTIONS from trusted origin succeeds with expected headers."""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": CANONICAL_PROD_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == CANONICAL_PROD_ORIGIN
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert "POST" in response.headers.get("access-control-allow-methods", "")

    def test_preflight_options_for_malicious_netlify_origin(self, client: TestClient) -> None:
        """Preflight OPTIONS from malicious Netlify site is rejected with 400 and no allow-origin."""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": MALICIOUS_NETLIFY_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        # Starlette rejects unauthorized preflights with 400
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers

    def test_preflight_options_for_localhost(self, client: TestClient) -> None:
        """Preflight OPTIONS from local development server succeeds."""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": DEV_127_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == DEV_127_ORIGIN
        assert response.headers.get("access-control-allow-credentials") == "true"


class TestProductionCORSConfigurationSafety:
    """Startup and configuration validation in production mode."""

    def test_production_rejects_wildcard_origin(self) -> None:
        """Production environment must refuse to start with ALLOWED_ORIGINS='*'."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                JWT_SECRET_KEY="a-strong-prod-secret-key-1234567890",
                ALLOWED_ORIGINS="*",
            )
        assert "ALLOWED_ORIGINS cannot contain '*'" in str(exc_info.value)

    def test_production_rejects_list_containing_wildcard(self) -> None:
        """Production environment must refuse ALLOWED_ORIGINS with '*' in comma-separated list."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                JWT_SECRET_KEY="a-strong-prod-secret-key-1234567890",
                ALLOWED_ORIGINS="https://oncovision-live.netlify.app, *",
            )
        assert "ALLOWED_ORIGINS cannot contain '*'" in str(exc_info.value)

    def test_production_rejects_empty_origins(self) -> None:
        """Production environment must refuse empty ALLOWED_ORIGINS."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                APP_ENV="production",
                JWT_SECRET_KEY="a-strong-prod-secret-key-1234567890",
                ALLOWED_ORIGINS="",
            )
        assert "ALLOWED_ORIGINS must contain at least one trusted origin" in str(exc_info.value)

    def test_production_accepts_explicit_origin_and_disables_regex(self) -> None:
        """Valid production settings contain only explicit origins and disable regex matching."""
        settings = Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="a-strong-prod-secret-key-1234567890",
            ALLOWED_ORIGINS="https://oncovision-live.netlify.app",
        )
        assert settings.is_production is True
        assert settings.cors_origin_regex is None
        assert settings.allowed_origins_list == ["https://oncovision-live.netlify.app"]
