"""Router-level tests for AI Chat endpoints (Phase 11 — LLM + RAG Integration).

Exercises:
- `POST /api/v1/chat/prediction/{prediction_id}`
- `POST /api/v1/chat/knowledge`
- `GET /api/v1/chat/history/{conversation_id}`
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
        full_name="Test Oncologist",
        email="oncologist@example.com",
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


class TestChatAuthorization:
    def test_unauthenticated_prediction_chat_returns_401(self) -> None:
        unauth_client = TestClient(app)
        pred_id = str(uuid.uuid4())
        resp = unauth_client.post(
            f"/api/v1/chat/prediction/{pred_id}",
            json={"message": "What does this mean?"},
        )
        assert resp.status_code == 401

    def test_unauthenticated_knowledge_chat_returns_401(self) -> None:
        unauth_client = TestClient(app)
        resp = unauth_client.post(
            "/api/v1/chat/knowledge",
            json={"message": "What is adenocarcinoma?"},
        )
        assert resp.status_code == 401

    def test_unauthenticated_chat_history_returns_401(self) -> None:
        unauth_client = TestClient(app)
        conv_id = str(uuid.uuid4())
        resp = unauth_client.get(f"/api/v1/chat/history/{conv_id}")
        assert resp.status_code == 401


class TestPredictionChat:
    @patch("app.api.v1.chat.ChatService.prediction_chat", new_callable=AsyncMock)
    def test_successful_prediction_chat(self, mock_pred_chat, client: TestClient, current_user: User) -> None:
        pred_id = uuid.uuid4()
        conv_id = uuid.uuid4()
        mock_pred_chat.return_value = {
            "response": "The prediction shows benign tissue characteristics.",
            "conversation_id": str(conv_id),
            "sources": None,
            "disclaimer": "Educational only.",
        }

        resp = client.post(
            f"/api/v1/chat/prediction/{pred_id}",
            json={"message": "Explain this result", "language": "en"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["response"] == "The prediction shows benign tissue characteristics."
        assert body["data"]["conversation_id"] == str(conv_id)

    def test_empty_message_returns_422(self, client: TestClient) -> None:
        pred_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/chat/prediction/{pred_id}",
            json={"message": ""},
        )
        assert resp.status_code == 422

    @patch("app.api.v1.chat.ChatService.prediction_chat", new_callable=AsyncMock)
    def test_prediction_chat_rate_limit_or_not_found(self, mock_pred_chat, client: TestClient) -> None:
        pred_id = uuid.uuid4()
        mock_pred_chat.side_effect = ValueError("Prediction not found or access denied")

        resp = client.post(
            f"/api/v1/chat/prediction/{pred_id}",
            json={"message": "Explain this"},
        )
        assert resp.status_code == 400
        assert "Prediction not found" in resp.json()["message"]


class TestKnowledgeChat:
    @patch("app.api.v1.chat.ChatService.knowledge_chat", new_callable=AsyncMock)
    def test_successful_knowledge_chat(self, mock_know_chat, client: TestClient) -> None:
        conv_id = uuid.uuid4()
        mock_know_chat.return_value = {
            "response": "Lung adenocarcinoma is a non-small cell lung cancer subtype.",
            "conversation_id": str(conv_id),
            "sources": [
                {
                    "title": "Lung Adenocarcinoma Overview",
                    "source": "lung_cancer/adenocarcinoma.md",
                    "relevance": 0.88,
                }
            ],
            "disclaimer": "Educational only.",
        }

        resp = client.post(
            "/api/v1/chat/knowledge",
            json={"message": "What is adenocarcinoma?", "language": "en"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "Lung adenocarcinoma" in body["data"]["response"]
        assert len(body["data"]["sources"]) == 1
        assert body["data"]["sources"][0]["relevance"] == 0.88


class TestChatHistory:
    @patch("app.api.v1.chat.ChatRepository.get_conversation", new_callable=AsyncMock)
    def test_get_chat_history(self, mock_get_history, client: TestClient, current_user: User) -> None:
        from unittest.mock import MagicMock
        from datetime import datetime, timezone

        conv_id = uuid.uuid4()
        msg_id = uuid.uuid4()

        mock_msg = MagicMock()
        mock_msg.id = msg_id
        mock_msg.user_id = current_user.id
        mock_msg.role = "user"
        mock_msg.content = "Hello AI"
        mock_msg.sources = None
        mock_msg.created_at = datetime.now(timezone.utc)

        mock_get_history.return_value = [mock_msg]

        resp = client.get(f"/api/v1/chat/history/{conv_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total"] == 1
        assert body["data"]["messages"][0]["content"] == "Hello AI"
