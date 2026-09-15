"""Router-level tests for AI Prediction Summary endpoints (Phase 11 — LLM + RAG Integration).

Exercises:
- `POST /api/v1/predictions/{prediction_id}/summary`
- `GET /api/v1/predictions/{prediction_id}/summary`
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.main import app
from app.models.enums import UserRole
from app.models.user import User


def _make_user() -> User:
    return User(
        id=uuid.uuid4(),
        full_name="Test Pathologist",
        email="pathologist@example.com",
        password_hash="not-a-real-hash",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def current_user() -> User:
    return _make_user()


@pytest.fixture
def client(current_user: User):
    """TestClient with authenticated user and fake db session."""
    fake_db = AsyncMock()

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: fake_db

    yield TestClient(app)

    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_db, None)


class TestSummaryAuthorization:
    def test_unauthenticated_generate_summary_returns_401(self) -> None:
        unauth_client = TestClient(app)
        pred_id = str(uuid.uuid4())
        resp = unauth_client.post(
            f"/api/v1/predictions/{pred_id}/summary",
            json={"language": "en"},
        )
        assert resp.status_code == 401

    def test_unauthenticated_get_summary_returns_401(self) -> None:
        unauth_client = TestClient(app)
        pred_id = str(uuid.uuid4())
        resp = unauth_client.get(f"/api/v1/predictions/{pred_id}/summary")
        assert resp.status_code == 401


class TestSummaryEndpoints:
    @patch("app.api.v1.summary.LLMSummaryService.generate_summary", new_callable=AsyncMock)
    def test_generate_summary_success(self, mock_gen_summary, client: TestClient) -> None:
        pred_id = uuid.uuid4()
        mock_gen_summary.return_value = {
            "summary_text": "High probability colon adenocarcinoma identified with 94.5% confidence.",
            "prediction_id": str(pred_id),
            "language": "en",
            "disclaimer": "Educational only.",
        }

        resp = client.post(
            f"/api/v1/predictions/{pred_id}/summary",
            json={"language": "en"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["prediction_id"] == str(pred_id)
        assert "colon adenocarcinoma" in body["data"]["summary_text"]

    @patch("app.api.v1.summary.LLMSummaryService.generate_summary", new_callable=AsyncMock)
    def test_generate_summary_not_found(self, mock_gen_summary, client: TestClient) -> None:
        pred_id = uuid.uuid4()
        mock_gen_summary.side_effect = ValueError("Prediction not found or access denied")

        resp = client.post(
            f"/api/v1/predictions/{pred_id}/summary",
            json={"language": "en"},
        )
        assert resp.status_code == 404
        assert "Prediction not found" in resp.json()["message"]

    @patch("app.api.v1.summary.LLMSummaryService.generate_summary", new_callable=AsyncMock)
    def test_get_summary_success(self, mock_gen_summary, client: TestClient) -> None:
        pred_id = uuid.uuid4()
        mock_gen_summary.return_value = {
            "summary_text": "Existing cached summary for histopathology slide.",
            "prediction_id": str(pred_id),
            "language": "en",
            "disclaimer": "Educational only.",
        }

        resp = client.get(f"/api/v1/predictions/{pred_id}/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["prediction_id"] == str(pred_id)
        assert "Existing cached summary" in body["data"]["summary_text"]
