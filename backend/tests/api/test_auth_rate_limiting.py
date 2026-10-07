"""Focused tests for authentication rate limiting (Phase 6.1-D, FINDING-05).

Verifies in-memory sliding window rate limits on /api/v1/auth/login and
/api/v1/auth/register:
1. Login rate limit enforcement (under limit succeeds, at limit returns 429).
2. Registration rate limit enforcement.
3. Safe Retry-After header calculation and delivery.
4. Window expiration and quota restoration.
5. Failed attempts count against limit; successful attempts do not bypass it.
6. Multi-dimensional keying prevents single-dimension bypass (credential stuffing from single IP).
7. Independent isolation between login, registration, and diagnostic LLM rate limiters.
8. Strict non-disclosure: no passwords, tokens, stack traces, or account-existence hints leaked.
"""

import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth import _login_rate_limiter, _register_rate_limiter
from app.api.v1.system import _llm_test_rate_limiter
from app.core.config import settings
from app.core.exceptions import InvalidCredentialsError
from app.dependencies.services import get_auth_service
from app.main import app
from app.models.enums import UserRole
from app.models.user import User

LOGIN_URL = "/api/v1/auth/login"
REGISTER_URL = "/api/v1/auth/register"


def _make_mock_user(email: str = "doctor@oncovision.org") -> User:
    from datetime import datetime, timezone
    return User(
        id=uuid.uuid4(),
        email=email,
        full_name="Dr. Test User",
        password_hash="$2b$12$e8YxRkG9F3O5Gf0.2j2Y..fakehashforunittests",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture(autouse=True)
def reset_limiters():
    """Ensure in-memory limiters start completely clean before and after each test."""
    _login_rate_limiter.reset()
    _register_rate_limiter.reset()
    _llm_test_rate_limiter.reset()
    yield
    _login_rate_limiter.reset()
    _register_rate_limiter.reset()
    _llm_test_rate_limiter.reset()


@pytest.fixture
def mock_auth_service():
    """Mock AuthService for isolated router-level rate limiting tests."""
    mock = MagicMock()
    user = _make_mock_user()
    mock.login = AsyncMock(return_value=(user, "access_token_abc", "refresh_token_xyz"))
    mock.register = AsyncMock(return_value=user)
    return mock


@pytest.fixture
def client(mock_auth_service) -> TestClient:
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service
    yield TestClient(app)
    app.dependency_overrides.pop(get_auth_service, None)


class TestLoginRateLimiting:
    """Tests for POST /api/v1/auth/login rate limiting."""

    def test_login_under_limit_succeeds(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 5)
        payload = {"email": "doctor@oncovision.org", "password": "SecurePassword123!"}

        for i in range(5):
            resp = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.1"})
            assert resp.status_code == 200, f"Request {i+1} should have succeeded"
            assert resp.json()["success"] is True

    def test_login_at_limit_returns_429(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 3)
        payload = {"email": "doctor@oncovision.org", "password": "SecurePassword123!"}

        # First 3 succeed
        for _ in range(3):
            resp = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.2"})
            assert resp.status_code == 200

        # 4th request must be rejected with 429
        blocked = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.2"})
        assert blocked.status_code == 429
        body = blocked.json()
        assert body["success"] is False
        assert "Too many authentication requests" in body["message"]

    def test_login_429_contains_valid_retry_after_header(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 2)
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS", 60)
        payload = {"email": "doctor@oncovision.org", "password": "SecurePassword123!"}

        client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.3"})
        client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.3"})

        blocked = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.3"})
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers
        retry_after = int(blocked.headers["Retry-After"])
        assert 1 <= retry_after <= 60

    def test_login_failed_attempts_are_rate_limited(
        self, client: TestClient, mock_auth_service: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Failed password attempts must count towards the rate limit, protecting against brute-force."""
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 3)
        mock_auth_service.login = AsyncMock(side_effect=InvalidCredentialsError("Invalid email or password."))

        payload = {"email": "doctor@oncovision.org", "password": "WrongPassword!"}

        for _ in range(3):
            resp = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.4"})
            assert resp.status_code == 401

        # 4th attempt must be 429 before touching auth_service
        blocked = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.4"})
        assert blocked.status_code == 429
        # auth_service.login was called exactly 3 times, not 4
        assert mock_auth_service.login.call_count == 3

    def test_login_window_expiration_resets_quota(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After window expires, subsequent login requests are permitted again."""
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 2)
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS", 10)
        payload = {"email": "doctor@oncovision.org", "password": "SecurePassword123!"}

        client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.5"})
        client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.5"})

        blocked = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.5"})
        assert blocked.status_code == 429

        # Simulate passage of time by backdating timestamps
        for k in _login_rate_limiter.requests:
            _login_rate_limiter.requests[k] = [t - 15.0 for t in _login_rate_limiter.requests[k]]

        # Now request should succeed again
        reopened = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.0.0.5"})
        assert reopened.status_code == 200

    def test_single_attacker_cannot_bypass_by_changing_email(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An attacker rotating emails from a single IP is blocked by the IP dimension."""
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 3)

        client.post(LOGIN_URL, json={"email": "victim1@oncovision.org", "password": "x"}, headers={"X-Forwarded-For": "198.51.100.10"})
        client.post(LOGIN_URL, json={"email": "victim2@oncovision.org", "password": "x"}, headers={"X-Forwarded-For": "198.51.100.10"})
        client.post(LOGIN_URL, json={"email": "victim3@oncovision.org", "password": "x"}, headers={"X-Forwarded-For": "198.51.100.10"})

        # 4th request with a brand new email from the same IP must still be blocked
        blocked = client.post(
            LOGIN_URL,
            json={"email": "victim4@oncovision.org", "password": "x"},
            headers={"X-Forwarded-For": "198.51.100.10"},
        )
        assert blocked.status_code == 429

    def test_different_ips_have_independent_quotas(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Legitimate user on another IP is not locked out when an attacker's IP is throttled."""
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 2)
        payload = {"email": "doctor@oncovision.org", "password": "SecurePassword123!"}

        # Attacker exhausts quota on IP 1
        client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "198.51.100.20"})
        client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "198.51.100.20"})
        assert client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "198.51.100.20"}).status_code == 429

        # Legitimate user from IP 2 logs in successfully
        legit = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "203.0.113.88"})
        assert legit.status_code == 200


class TestRegistrationRateLimiting:
    """Tests for POST /api/v1/auth/register rate limiting."""

    def test_register_under_limit_succeeds(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "AUTH_REGISTER_RATE_LIMIT_MAX_REQUESTS", 3)
        payload = {
            "email": "newuser@oncovision.org",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "full_name": "New User",
        }

        for i in range(3):
            resp = client.post(REGISTER_URL, json=payload, headers={"X-Forwarded-For": f"10.1.0.{i+1}"})
            assert resp.status_code == 201

    def test_register_at_limit_returns_429(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "AUTH_REGISTER_RATE_LIMIT_MAX_REQUESTS", 2)
        payload = {
            "email": "bot@oncovision.org",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "full_name": "Bot User",
        }

        client.post(REGISTER_URL, json=payload, headers={"X-Forwarded-For": "10.1.0.99"})
        client.post(REGISTER_URL, json=payload, headers={"X-Forwarded-For": "10.1.0.99"})

        # 3rd request from same IP must be 429
        blocked = client.post(REGISTER_URL, json=payload, headers={"X-Forwarded-For": "10.1.0.99"})
        assert blocked.status_code == 429
        assert blocked.json()["success"] is False
        assert "Retry-After" in blocked.headers

    def test_automated_registration_rotating_email_from_same_ip_is_blocked(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An attacker generating bot accounts from a single IP is blocked by the IP limit."""
        monkeypatch.setattr(settings, "AUTH_REGISTER_RATE_LIMIT_MAX_REQUESTS", 2)

        client.post(
            REGISTER_URL,
            json={
                "email": "bot1@oncovision.org",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "full_name": "Bot 1",
            },
            headers={"X-Forwarded-For": "198.51.100.50"},
        )
        client.post(
            REGISTER_URL,
            json={
                "email": "bot2@oncovision.org",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "full_name": "Bot 2",
            },
            headers={"X-Forwarded-For": "198.51.100.50"},
        )

        # 3rd registration with a different email is blocked
        blocked = client.post(
            REGISTER_URL,
            json={
                "email": "bot3@oncovision.org",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "full_name": "Bot 3",
            },
            headers={"X-Forwarded-For": "198.51.100.50"},
        )
        assert blocked.status_code == 429


class TestRateLimiterIsolation:
    """Verify isolation between independent rate limiters and other endpoints."""

    def test_login_exhaustion_does_not_affect_registration(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 2)
        login_payload = {"email": "doctor@oncovision.org", "password": "SecurePassword123!"}

        # Exhaust login limit
        client.post(LOGIN_URL, json=login_payload, headers={"X-Forwarded-For": "10.2.0.1"})
        client.post(LOGIN_URL, json=login_payload, headers={"X-Forwarded-For": "10.2.0.1"})
        assert client.post(LOGIN_URL, json=login_payload, headers={"X-Forwarded-For": "10.2.0.1"}).status_code == 429

        # Register from same IP must succeed normally
        reg_payload = {
            "email": "new@oncovision.org",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "full_name": "New User",
        }
        reg_resp = client.post(REGISTER_URL, json=reg_payload, headers={"X-Forwarded-For": "10.2.0.1"})
        assert reg_resp.status_code == 201

    def test_exhausted_auth_does_not_affect_health_or_system(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 1)
        login_payload = {"email": "doctor@oncovision.org", "password": "Password123!"}

        # Exhaust login
        client.post(LOGIN_URL, json=login_payload, headers={"X-Forwarded-For": "10.2.0.2"})
        assert client.post(LOGIN_URL, json=login_payload, headers={"X-Forwarded-For": "10.2.0.2"}).status_code == 429

        # Health endpoint remains unaffected
        health_resp = client.get("/api/v1/health")
        assert health_resp.status_code == 200

        # Root endpoint remains unaffected
        root_resp = client.get("/")
        assert root_resp.status_code == 200


class TestSecurityAndNonDisclosure:
    """Ensure 429 responses never disclose sensitive parameters or internal state."""

    def test_no_sensitive_data_in_login_429_body(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        secret_password = "SuperSecretPlainTextPassword!#$99"
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 1)
        payload = {"email": "doctor@oncovision.org", "password": secret_password}

        client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.3.0.1"})
        blocked = client.post(LOGIN_URL, json=payload, headers={"X-Forwarded-For": "10.3.0.1"})

        assert blocked.status_code == 429
        body_text = blocked.text
        assert secret_password not in body_text
        assert "password" not in body_text.lower()
        assert "traceback" not in body_text.lower()
        assert "exception" not in body_text.lower()
        assert "sql" not in body_text.lower()

    def test_account_existence_not_disclosed_when_throttled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """429 responses for existing vs non-existing accounts are strictly indistinguishable."""
        monkeypatch.setattr(settings, "AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS", 1)

        # IP 1 throttled with known email
        client.post(LOGIN_URL, json={"email": "existing@oncovision.org", "password": "p"}, headers={"X-Forwarded-For": "10.3.0.2"})
        blocked_existing = client.post(
            LOGIN_URL, json={"email": "existing@oncovision.org", "password": "p"}, headers={"X-Forwarded-For": "10.3.0.2"}
        )

        # IP 2 throttled with nonexistent email
        client.post(LOGIN_URL, json={"email": "unknown_random_xyz@oncovision.org", "password": "p"}, headers={"X-Forwarded-For": "10.3.0.3"})
        blocked_unknown = client.post(
            LOGIN_URL, json={"email": "unknown_random_xyz@oncovision.org", "password": "p"}, headers={"X-Forwarded-For": "10.3.0.3"}
        )

        assert blocked_existing.status_code == 429
        assert blocked_unknown.status_code == 429
        assert blocked_existing.json()["message"] == blocked_unknown.json()["message"]
