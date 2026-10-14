"""Tests for Admin Knowledgebase Ingestion endpoint (POST /api/v1/admin/knowledge/ingest).

Covers:
1. Feature flag disabled by default (returns 404 without invoking ingestion).
2. Unauthenticated request returns 401 when flag is enabled.
3. Non-admin request returns 403 when flag is enabled.
4. Admin dry-run (default and explicit) returns 200 with discovery/chunk statistics and 0 embedding calls.
5. Live ingestion without explicit opt-in confirmation returns 400 Bad Request.
6. Live ingestion with explicit confirmation invokes the pipeline with dry_run=False.
7. Concurrent requests return 409 Conflict while worker lock is held.
8. Sanitized error messages in HTTP 500 responses (redacting keys, database URLs, and secrets).
9. Zero disclosure of passwords, API keys, or database URLs in responses.
"""

import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api.v1.admin.knowledge import _ingestion_lock, _sanitize_error
from app.core.settings import get_settings
from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.main import app
from app.models.enums import UserRole
from app.rag.ingestion import IngestionStats
from tests.admin.doubles import make_user

ENDPOINT_PATH = "/api/v1/admin/knowledge/ingest"


@pytest.fixture
def admin_user():
    return make_user(role=UserRole.ADMIN, email="admin@example.com")


@pytest.fixture
def standard_user():
    return make_user(role=UserRole.USER, email="user@example.com")


@pytest.fixture(autouse=True)
def clean_overrides_and_lock():
    """Ensure clean dependency overrides and released lock before and after each test."""
    app.dependency_overrides.clear()
    if _ingestion_lock.locked():
        # Force unlock if left in locked state by a test
        try:
            _ingestion_lock.release()
        except RuntimeError:
            pass
    yield
    app.dependency_overrides.clear()
    if _ingestion_lock.locked():
        try:
            _ingestion_lock.release()
        except RuntimeError:
            pass


class TestAdminKnowledgeIngestionFeatureFlag:
    def test_endpoint_disabled_by_default_returns_404(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that with ADMIN_INGESTION_ENDPOINT_ENABLED=False (default), 404 is returned."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", False)

        client = TestClient(app)
        response = client.post(ENDPOINT_PATH, json={})
        assert response.status_code == 404
        assert "not found or disabled" in response.text.lower()

    def test_endpoint_disabled_even_for_admin_returns_404(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Even an authenticated admin receives 404 when the feature flag is disabled."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", False)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        client = TestClient(app)
        response = client.post(ENDPOINT_PATH, json={})
        assert response.status_code == 404


class TestAdminKnowledgeIngestionAuthorization:
    def test_unauthenticated_request_returns_401_when_enabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When enabled, an unauthenticated request must receive 401 Unauthorized."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)

        client = TestClient(app)
        response = client.post(ENDPOINT_PATH, json={})
        assert response.status_code == 401

    def test_non_admin_request_returns_403_when_enabled(
        self, standard_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When enabled, a regular user (non-admin) must receive 403 Forbidden."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        app.dependency_overrides[get_current_active_user] = lambda: standard_user

        client = TestClient(app)
        response = client.post(ENDPOINT_PATH, json={})
        assert response.status_code == 403


class TestAdminKnowledgeIngestionDryRun:
    def test_default_request_is_dry_run_and_writes_nothing(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Default POST payload runs in dry-run mode, creates no embeddings, and calls no DB."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        client = TestClient(app)
        # Empty body defaults to dry_run=True, confirm_live_ingestion=False
        response = client.post(ENDPOINT_PATH, json={})
        assert response.status_code == 200

        data = response.json()["data"]
        assert data["dry_run"] is True
        assert data["documents_discovered"] == 40
        assert data["documents_ingested"] == 40
        assert data["chunks_created"] == 146
        assert data["embedding_api_calls"] == 0
        assert "dry-run" in response.json()["message"].lower()

    def test_explicit_dry_run_with_target_document_filter(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit dry_run=True with target_document filters discovery to that document."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        client = TestClient(app)
        response = client.post(
            ENDPOINT_PATH,
            json={"dry_run": True, "target_document": "lung_adenocarcinoma_morphology.md"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["dry_run"] is True
        assert data["documents_discovered"] == 40
        assert data["documents_ingested"] == 1
        assert data["embedding_api_calls"] == 0


class TestAdminKnowledgeIngestionLiveOptIn:
    def test_live_ingestion_without_opt_in_returns_400(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Attempting dry_run=False without confirm_live_ingestion=True returns 400 Bad Request."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        client = TestClient(app)
        response = client.post(ENDPOINT_PATH, json={"dry_run": False})
        assert response.status_code == 400
        assert "confirm_live_ingestion=True" in response.text

    def test_live_ingestion_with_opt_in_invokes_pipeline(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Live ingestion with explicit opt-in confirmation proceeds and calls pipeline."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        monkeypatch.setattr(settings, "GOOGLE_API_KEY", "test-fake-key")
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        fake_db = AsyncMock()
        async def fake_get_db():
            yield fake_db
        app.dependency_overrides[get_db] = fake_get_db

        mock_stats = IngestionStats()
        mock_stats.documents_discovered = 40
        mock_stats.documents_ingested = 40
        mock_stats.chunks_created = 146
        mock_stats.embedding_api_calls = 40

        with patch("app.rag.ingestion.DocumentIngestionPipeline.ingest_corpus", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = mock_stats
            with patch("app.llm.client.get_gemini_client"):
                client = TestClient(app)
                response = client.post(
                    ENDPOINT_PATH,
                    json={"dry_run": False, "confirm_live_ingestion": True},
                )
                assert response.status_code == 200
                data = response.json()["data"]
                assert data["dry_run"] is False
                assert data["embedding_api_calls"] == 40
                assert mock_ingest.call_count == 1
                call_kwargs = mock_ingest.call_args[1]
                assert call_kwargs["dry_run"] is False
                assert call_kwargs["session"] == fake_db


class TestAdminKnowledgeIngestionConcurrency:
    def test_concurrent_request_returns_409_conflict(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If an ingestion run is already holding the lock, concurrent requests receive 409 Conflict."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        # Mock _ingestion_lock.locked to simulate an active job
        monkeypatch.setattr(_ingestion_lock, "locked", lambda: True)
        client = TestClient(app)
        response = client.post(ENDPOINT_PATH, json={})
        assert response.status_code == 409
        assert "already in progress" in response.text.lower()


class TestAdminKnowledgeIngestionErrorSanitization:
    def test_sanitizer_redacts_keys_urls_and_passwords(self) -> None:
        """Verify _sanitize_error strips API keys, DB connection strings, and passwords."""
        raw_error = (
            "Failed connecting to postgresql+asyncpg://admin:supersecret@db.internal:5432/production "
            "with key AIzaSyFakeApiKey123456789012345 and password=super_password_99"
        )
        sanitized = _sanitize_error(raw_error, "AIzaSyFakeApiKey123456789012345")
        assert "supersecret" not in sanitized
        assert "AIzaSyFakeApiKey123456789012345" not in sanitized
        assert "super_password_99" not in sanitized
        assert "[REDACTED_API_KEY]" in sanitized
        assert "[REDACTED_DATABASE_URL]" in sanitized
        assert "[REDACTED_PASSWORD]" in sanitized

    def test_exception_during_ingestion_returns_500_sanitized(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When an unhandled exception occurs, the 500 response message must not disclose secrets."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        with patch("app.rag.ingestion.DocumentIngestionPipeline.ingest_corpus", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.side_effect = RuntimeError(
                "Internal DB error: postgresql://admin:secret123@neon.tech/oncovision with AIzaSyKey9876543210"
            )
            client = TestClient(app)
            response = client.post(ENDPOINT_PATH, json={})
            assert response.status_code == 500
            body = response.text
            assert "secret123" not in body
            assert "AIzaSyKey9876543210" not in body
            assert "[REDACTED_DATABASE_URL]" in body
            assert "[REDACTED_API_KEY]" in body

    def test_response_never_contains_secret_looking_keys(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify standard 200 response contains no secret-looking tokens."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        client = TestClient(app)
        response = client.post(ENDPOINT_PATH, json={})
        assert response.status_code == 200

        body_lower = response.text.lower()
        for forbidden in ("password", "secret", "database_url", "jwt_secret", "aiza"):
            assert forbidden not in body_lower


class TestAdminKnowledgeIngestionMessageAccuracy:
    """Verifies that API message string accurately reflects success vs completion with errors."""

    def test_successful_dry_run_retains_success_message(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Successful dry-run returns 'Knowledgebase dry-run completed successfully.'."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        mock_stats = IngestionStats(dry_run=True)
        mock_stats.documents_discovered = 40
        mock_stats.documents_ingested = 40
        mock_stats.chunks_created = 146

        with patch("app.rag.ingestion.DocumentIngestionPipeline.ingest_corpus", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = mock_stats
            client = TestClient(app)
            response = client.post(ENDPOINT_PATH, json={"dry_run": True})
            assert response.status_code == 200
            assert response.json()["message"] == "Knowledgebase dry-run completed successfully."

    def test_successful_live_ingestion_retains_success_message(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Successful live ingestion returns 'Knowledgebase live ingestion completed successfully.'."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        monkeypatch.setattr(settings, "GOOGLE_API_KEY", "test-fake-key")
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        fake_db = AsyncMock()
        async def fake_get_db():
            yield fake_db
        app.dependency_overrides[get_db] = fake_get_db

        mock_stats = IngestionStats(dry_run=False)
        mock_stats.documents_discovered = 40
        mock_stats.documents_ingested = 40
        mock_stats.chunks_created = 146
        mock_stats.embedding_api_calls = 40

        with patch("app.rag.ingestion.DocumentIngestionPipeline.ingest_corpus", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = mock_stats
            with patch("app.llm.client.get_gemini_client"):
                client = TestClient(app)
                response = client.post(
                    ENDPOINT_PATH,
                    json={"dry_run": False, "confirm_live_ingestion": True},
                )
                assert response.status_code == 200
                assert response.json()["message"] == "Knowledgebase live ingestion completed successfully."

    def test_dry_run_with_errors_returns_completed_with_errors_message(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dry-run with errors returns 'Knowledgebase dry-run completed with errors.'."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        mock_stats = IngestionStats(dry_run=True)
        mock_stats.documents_discovered = 40
        mock_stats.documents_ingested = 39
        mock_stats.chunks_created = 140
        mock_stats.errors = ["Simulated discovery parsing error in test_doc.md"]

        with patch("app.rag.ingestion.DocumentIngestionPipeline.ingest_corpus", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = mock_stats
            client = TestClient(app)
            response = client.post(ENDPOINT_PATH, json={"dry_run": True})
            assert response.status_code == 200
            assert response.json()["message"] == "Knowledgebase dry-run completed with errors."
            assert len(response.json()["data"]["errors"]) == 1

    def test_live_ingestion_with_errors_returns_completed_with_errors_message(
        self, admin_user, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Live ingestion with errors returns 'Knowledgebase live ingestion completed with errors.'."""
        settings = get_settings()
        monkeypatch.setattr(settings, "ADMIN_INGESTION_ENDPOINT_ENABLED", True)
        monkeypatch.setattr(settings, "GOOGLE_API_KEY", "test-fake-key")
        app.dependency_overrides[get_current_active_user] = lambda: admin_user

        fake_db = AsyncMock()
        async def fake_get_db():
            yield fake_db
        app.dependency_overrides[get_db] = fake_get_db

        mock_stats = IngestionStats(dry_run=False)
        mock_stats.documents_discovered = 40
        mock_stats.documents_ingested = 38
        mock_stats.chunks_created = 135
        mock_stats.embedding_api_calls = 38
        mock_stats.errors = [
            "Error ingesting document doc1.md: Simulated DB timeout",
            "Error ingesting document doc2.md: Simulated commit deadlock",
        ]

        with patch("app.rag.ingestion.DocumentIngestionPipeline.ingest_corpus", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = mock_stats
            with patch("app.llm.client.get_gemini_client"):
                client = TestClient(app)
                response = client.post(
                    ENDPOINT_PATH,
                    json={"dry_run": False, "confirm_live_ingestion": True},
                )
                assert response.status_code == 200
                assert response.json()["message"] == "Knowledgebase live ingestion completed with errors."
                assert len(response.json()["data"]["errors"]) == 2
