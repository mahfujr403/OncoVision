"""Security and reliability tests for /api/v1/system/test-llm (Phase 6.1-A).

Verifies:
1. Unauthenticated requests return 401 Unauthorized.
2. Authenticated non-admin users return 403 Forbidden.
3. Authenticated inactive users return 403 Forbidden.
4. Authenticated administrators succeed with 200 OK.
5. In-memory sliding window rate limiting rejects excessive calls with 429 Too Many Requests.
6. Diagnostic response does not disclose secrets, API keys, or credentials.
7. Upstream Gemini API errors are sanitized and do not leak API keys, URLs, or internal traces.
8. Unconfigured GOOGLE_API_KEY returns safe diagnostic warning without calling upstream.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.v1.system import _llm_test_rate_limiter
from app.core.exceptions import InactiveUserError
from app.core.settings import get_settings
from app.dependencies.auth import get_current_active_user, get_current_user
from app.main import app
from app.models.enums import UserRole
from tests.admin.doubles import make_user

TEST_LLM_PATH = "/api/v1/system/test-llm"


class FakeModel:
    def __init__(self, name: str):
        self.name = name


class FakeGenAIClientSuccess:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.models = self
        self.aio = self

    def list(self):
        return [
            FakeModel("models/gemini-1.5-flash"),
            FakeModel("models/gemini-1.5-pro"),
            FakeModel("models/gemini-2.5-flash"),
            FakeModel("models/gemini-2.0-flash"),
            FakeModel("models/gemini-3.6-flash"),
            FakeModel("models/gemini-embedding-2"),
        ]

    async def generate_content(self, model: str, contents: str):
        class FakeResponse:
            text = f"Healthy response from {model}"
        return FakeResponse()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset diagnostic rate limiter state before each test."""
    _llm_test_rate_limiter.requests.clear()
    yield
    _llm_test_rate_limiter.requests.clear()
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user():
    return make_user(role=UserRole.ADMIN, email="admin@example.com")


@pytest.fixture
def standard_user():
    return make_user(role=UserRole.USER, email="user@example.com")


@pytest.fixture
def inactive_admin():
    return make_user(role=UserRole.ADMIN, email="inactive_admin@example.com", is_active=False)


def _client_with_user(user) -> TestClient:
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app)


class TestSystemTestLLMAuthenticationAndAuthorization:
    """Authentication and role boundary verification."""

    def test_unauthenticated_request_returns_401(self) -> None:
        client = TestClient(app)
        response = client.get(TEST_LLM_PATH)
        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False

    def test_authenticated_non_admin_returns_403(self, standard_user) -> None:
        client = _client_with_user(standard_user)
        response = client.get(TEST_LLM_PATH)
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False

    def test_authenticated_inactive_user_returns_403(self, inactive_admin) -> None:
        async def fake_get_current_user():
            if not inactive_admin.is_active:
                raise InactiveUserError()
            return inactive_admin

        app.dependency_overrides[get_current_user] = fake_get_current_user
        client = TestClient(app)
        response = client.get(TEST_LLM_PATH)
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False

    def test_authenticated_admin_request_succeeds_200(self, admin_user, monkeypatch) -> None:
        monkeypatch.setattr("google.genai.Client", FakeGenAIClientSuccess)
        client = _client_with_user(admin_user)
        response = client.get(TEST_LLM_PATH)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "data" in body
        assert body["data"]["configured_model"] is not None
        assert len(body["data"]["available_models"]) > 0


class TestSystemTestLLMRateLimiting:
    """Sliding window rate-limiting verification."""

    def test_rate_limit_exceeded_returns_429(self, admin_user, monkeypatch) -> None:
        monkeypatch.setattr("google.genai.Client", FakeGenAIClientSuccess)
        settings = get_settings()
        limit = settings.SYSTEM_TEST_LLM_RATE_LIMIT_MAX_REQUESTS

        client = _client_with_user(admin_user)
        # Execute up to the limit
        for i in range(limit):
            resp = client.get(TEST_LLM_PATH)
            assert resp.status_code == 200, f"Request {i+1} failed unexpectedly"

        # The next request within window must be rejected with 429
        rejected = client.get(TEST_LLM_PATH)
        assert rejected.status_code == 429
        body = rejected.json()
        assert body["success"] is False
        assert "rate limit exceeded" in body["message"].lower()


class TestSystemTestLLMInformationDisclosureAndErrorSanitization:
    """Information disclosure and exception sanitization verification."""

    def test_response_never_exposes_secrets_or_api_keys(self, admin_user, monkeypatch) -> None:
        monkeypatch.setattr("google.genai.Client", FakeGenAIClientSuccess)
        client = _client_with_user(admin_user)
        response = client.get(TEST_LLM_PATH)
        assert response.status_code == 200

        body_text = response.text.lower()
        for forbidden in ("password", "secret", "database_url", "jwt_secret"):
            assert forbidden not in body_text

    def test_upstream_gemini_error_sanitizes_keys_and_urls(self, admin_user, monkeypatch) -> None:
        fake_secret_key = "AIzaSyD-TEST_LEAK_SECRET_KEY_12345678"

        class FakeGenAIClientError:
            def __init__(self, api_key: str | None = None):
                self.models = self
                self.aio = self

            def list(self):
                raise RuntimeError(
                    f"Google API request to https://generativelanguage.googleapis.com/v1beta/models failed with key {fake_secret_key}"
                )

            async def generate_content(self, model: str, contents: str):
                raise RuntimeError(
                    f"Call to https://generativelanguage.googleapis.com/v1beta/{model}:generateContent failed with key {fake_secret_key}"
                )

        monkeypatch.setattr("google.genai.Client", FakeGenAIClientError)
        client = _client_with_user(admin_user)
        response = client.get(TEST_LLM_PATH)

        assert response.status_code == 200
        body = response.json()
        data = body["data"]

        # Ensure fake API key and URL are never leaked in response
        response_text = response.text
        assert fake_secret_key not in response_text
        assert "https://generativelanguage.googleapis.com" not in response_text

        # Verify redaction tokens appear instead
        assert "[REDACTED_API_KEY]" in data.get("list_error", "") or "[REDACTED_URL]" in data.get("list_error", "")

    def test_upstream_quota_error_classified_safely(self, admin_user, monkeypatch) -> None:
        class FakeGenAIClientQuotaError:
            def __init__(self, api_key: str | None = None):
                self.models = self
                self.aio = self

            def list(self):
                return [FakeModel("models/gemini-1.5-flash")]

            async def generate_content(self, model: str, contents: str):
                raise RuntimeError("429 Resource Exhausted: quota exceeded for model")

        monkeypatch.setattr("google.genai.Client", FakeGenAIClientQuotaError)
        client = _client_with_user(admin_user)
        response = client.get(TEST_LLM_PATH)

        assert response.status_code == 200
        body = response.json()
        res = body["data"]["test_results"]["gemini-1.5-flash"]
        assert res["status"] == "error"
        assert "quota exceeded" in res["error"].lower()

    def test_unconfigured_api_key_returns_safe_warning(self, admin_user, monkeypatch) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "GOOGLE_API_KEY", "")

        client = _client_with_user(admin_user)
        response = client.get(TEST_LLM_PATH)

        assert response.status_code == 200
        body = response.json()
        assert body["data"]["warning"] == "GOOGLE_API_KEY is not configured."
