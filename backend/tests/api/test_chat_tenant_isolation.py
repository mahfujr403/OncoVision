"""Tests for Phase 6.2 — Tenant Isolation & Request Boundary Hardening.

Covers:
- Phase 6.2-A: Conversation Ownership & Tenant Isolation (IDOR Prevention)
  * Knowledge chat ownership
  * Prediction chat ownership
  * Conversation history isolation (no cross-user leakage)
  * Non-existent vs foreign conversation indistinguishability (uniform 404/400)
  * Multi-user independence
  * Unauthenticated rejection
- Phase 6.2-B: Chat Input Boundary Hardening
  * Whitespace-only rejection (422)
  * Empty message rejection (422)
  * Configurable length limit (CHAT_MAX_MESSAGE_LENGTH = 2000)
  * Messages exceeding limit rejected before expensive RAG/LLM invocation
  * Valid messages up to limit accepted
  * Malformed identifiers rejected with 422
- Phase 6.2-C: Error & Data Leakage Hardening
  * Summary endpoint internal exceptions sanitized to generic messages
  * No stack traces, file paths, database connection strings, or credentials leaked
  * request_id preserved in error response envelopes
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.models.prediction_history import PredictionHistoryRecord
from app.repositories.chat_repository import ChatRepository
from app.services.chat_service import ChatService


def _create_user(name: str) -> User:
    return User(
        id=uuid.uuid4(),
        full_name=name,
        email=f"{name.lower().replace(' ', '')}@example.com",
        password_hash="fake_hash",
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )


# ==============================================================================
# Phase 6.2-A: Service-Level Conversation Ownership & IDOR Protection Tests
# ==============================================================================


class TestChatServiceTenantIsolation:
    """Proves conversation ownership enforcement in ChatService."""

    def test_knowledge_chat_creates_new_conversation_when_id_is_none(self) -> None:
        """When conversation_id is None, a new conversation UUID is generated and owned by the caller."""
        async def _run() -> None:
            user = _create_user("User A")
            mock_session = AsyncMock()
            service = ChatService(mock_session)

            service.repo.count_user_messages_in_window = AsyncMock(return_value=0)
            service.repo.create = AsyncMock()
            service.repo.get_conversation = AsyncMock(return_value=[])

            from app.rag.safety import DIAGNOSIS_REFUSAL_MESSAGE, SafetyBoundary, SafetyEvaluation
            from app.rag.schemas import GroundedAnswer

            service.generator.safety.evaluate_query = MagicMock(
                return_value=SafetyEvaluation(
                    boundary=SafetyBoundary.DIAGNOSIS,
                    requires_deterministic_refusal=True,
                    refusal_message=DIAGNOSIS_REFUSAL_MESSAGE,
                )
            )

            service.generator.generate_grounded_answer = AsyncMock(
                return_value=GroundedAnswer(
                    answer="Safe response",
                    citations=[],
                    grounded=True,
                    refusal_reason=None,
                    scope=None,
                    latency_ms=10.0,
                    request_id=None,
                )
            )

            result = await service.knowledge_chat(
                user_id=user.id,
                message="What is adenocarcinoma?",
                conversation_id=None,
            )

            assert "conversation_id" in result
            created_conv_id = uuid.UUID(result["conversation_id"])
            assert created_conv_id is not None
            service.repo.create.assert_called()
            first_call_msg = service.repo.create.call_args_list[0][0][0]
            assert first_call_msg.user_id == user.id
            assert first_call_msg.conversation_id == created_conv_id

        asyncio.run(_run())

    def test_knowledge_chat_allows_owner_to_continue_own_conversation(self) -> None:
        """User A can continue their existing knowledge conversation."""
        async def _run() -> None:
            user_a = _create_user("User A")
            conv_id = uuid.uuid4()
            mock_session = AsyncMock()
            service = ChatService(mock_session)

            service.repo.count_user_messages_in_window = AsyncMock(return_value=0)
            service.repo.get_conversation_metadata = AsyncMock(return_value={
                "user_id": user_a.id,
                "chat_type": "knowledge",
                "prediction_id": None,
            })
            service.repo.create = AsyncMock()
            service.repo.get_conversation = AsyncMock(return_value=[])

            from app.rag.safety import DIAGNOSIS_REFUSAL_MESSAGE, SafetyBoundary, SafetyEvaluation
            from app.rag.schemas import GroundedAnswer

            service.generator.safety.evaluate_query = MagicMock(
                return_value=SafetyEvaluation(
                    boundary=SafetyBoundary.DIAGNOSIS,
                    requires_deterministic_refusal=True,
                    refusal_message=DIAGNOSIS_REFUSAL_MESSAGE,
                )
            )

            service.generator.generate_grounded_answer = AsyncMock(
                return_value=GroundedAnswer(
                    answer="Owner response",
                    citations=[],
                    grounded=True,
                    refusal_reason=None,
                    scope=None,
                    latency_ms=10.0,
                    request_id=None,
                )
            )

            result = await service.knowledge_chat(
                user_id=user_a.id,
                message="Follow-up question",
                conversation_id=conv_id,
            )

            assert result["conversation_id"] == str(conv_id)
            service.repo.get_conversation_metadata.assert_called_once_with(conv_id)

        asyncio.run(_run())

    def test_knowledge_chat_blocks_foreign_user_from_accessing_conversation(self) -> None:
        """User B cannot access or continue User A's conversation."""
        async def _run() -> None:
            user_a = _create_user("User A")
            user_b = _create_user("User B")
            conv_id = uuid.uuid4()
            mock_session = AsyncMock()
            service = ChatService(mock_session)

            service.repo.count_user_messages_in_window = AsyncMock(return_value=0)
            service.repo.get_conversation_metadata = AsyncMock(return_value={
                "user_id": user_a.id,
                "chat_type": "knowledge",
                "prediction_id": None,
            })
            service.repo.create = AsyncMock()

            with pytest.raises(ValueError, match="Conversation not found or access denied."):
                await service.knowledge_chat(
                    user_id=user_b.id,
                    message="Malicious injection attempt",
                    conversation_id=conv_id,
                )

            service.repo.create.assert_not_called()

        asyncio.run(_run())

    def test_knowledge_chat_rejects_nonexistent_conversation_id(self) -> None:
        """A nonexistent conversation ID is safely rejected with identical error."""
        async def _run() -> None:
            user = _create_user("User A")
            random_conv_id = uuid.uuid4()
            mock_session = AsyncMock()
            service = ChatService(mock_session)

            service.repo.count_user_messages_in_window = AsyncMock(return_value=0)
            service.repo.get_conversation_metadata = AsyncMock(return_value=None)
            service.repo.create = AsyncMock()

            with pytest.raises(ValueError, match="Conversation not found or access denied."):
                await service.knowledge_chat(
                    user_id=user.id,
                    message="Hello",
                    conversation_id=random_conv_id,
                )

            service.repo.create.assert_not_called()

        asyncio.run(_run())

    def test_prediction_chat_blocks_foreign_user_from_accessing_conversation(self) -> None:
        """User B cannot access User A's prediction conversation."""
        async def _run() -> None:
            user_a = _create_user("User A")
            user_b = _create_user("User B")
            conv_id = uuid.uuid4()
            pred_id = uuid.uuid4()
            mock_session = AsyncMock()

            mock_pred = PredictionHistoryRecord(
                id=pred_id,
                user_id=user_b.id,
                predicted_class="lung_aca",
                confidence=0.95,
                agreement_ratio=1.0,
                summary=None,
            )
            fake_result = MagicMock()
            fake_result.scalar_one_or_none.return_value = mock_pred
            mock_session.execute = AsyncMock(return_value=fake_result)

            service = ChatService(mock_session)
            service.repo.count_user_messages_in_window = AsyncMock(return_value=0)
            # Conversation belongs to User A
            service.repo.get_conversation_metadata = AsyncMock(return_value={
                "user_id": user_a.id,
                "chat_type": "prediction",
                "prediction_id": pred_id,
            })
            service.repo.create = AsyncMock()

            with pytest.raises(ValueError, match="Conversation not found or access denied."):
                await service.prediction_chat(
                    user_id=user_b.id,
                    prediction_id=pred_id,
                    message="Tell me about this result",
                    conversation_id=conv_id,
                )

            service.repo.create.assert_not_called()

        asyncio.run(_run())

    def test_prediction_chat_blocks_cross_prediction_conversation_reuse(self) -> None:
        """User A cannot cross-wire a conversation from prediction 1 into prediction 2."""
        async def _run() -> None:
            user_a = _create_user("User A")
            conv_id = uuid.uuid4()
            pred_1 = uuid.uuid4()
            pred_2 = uuid.uuid4()
            mock_session = AsyncMock()

            mock_pred2 = PredictionHistoryRecord(
                id=pred_2,
                user_id=user_a.id,
                predicted_class="lung_scc",
                confidence=0.88,
                agreement_ratio=1.0,
                summary=None,
            )
            fake_result = MagicMock()
            fake_result.scalar_one_or_none.return_value = mock_pred2
            mock_session.execute = AsyncMock(return_value=fake_result)

            service = ChatService(mock_session)
            service.repo.count_user_messages_in_window = AsyncMock(return_value=0)
            # Conversation is owned by user_a, but was created under pred_1
            service.repo.get_conversation_metadata = AsyncMock(return_value={
                "user_id": user_a.id,
                "chat_type": "prediction",
                "prediction_id": pred_1,
            })
            service.repo.create = AsyncMock()

            with pytest.raises(ValueError, match="Conversation not found or access denied."):
                await service.prediction_chat(
                    user_id=user_a.id,
                    prediction_id=pred_2,
                    message="Switch prediction",
                    conversation_id=conv_id,
                )

            service.repo.create.assert_not_called()

        asyncio.run(_run())


# ==============================================================================
# Phase 6.2-A: API Router IDOR & Tenant Isolation Tests
# ==============================================================================


class TestChatAPITenantIsolation:
    """Verifies that API endpoints enforce tenant isolation across distinct users."""

    def test_unauthenticated_requests_are_denied(self) -> None:
        """All chat endpoints return 401 when called without credentials."""
        client = TestClient(app)
        conv_id = uuid.uuid4()
        pred_id = uuid.uuid4()

        r1 = client.post("/api/v1/chat/knowledge", json={"message": "hello"})
        assert r1.status_code == 401

        r2 = client.post(f"/api/v1/chat/prediction/{pred_id}", json={"message": "hello"})
        assert r2.status_code == 401

        r3 = client.get(f"/api/v1/chat/history/{conv_id}")
        assert r3.status_code == 401

    @patch("app.api.v1.chat.ChatService.knowledge_chat", new_callable=AsyncMock)
    def test_user_b_denied_access_to_user_a_knowledge_conversation(self, mock_know_chat) -> None:
        """User B passing User A's conversation ID receives 400 without data leakage."""
        user_b = _create_user("User B")
        conv_a_id = uuid.uuid4()

        mock_know_chat.side_effect = ValueError("Conversation not found or access denied.")

        app.dependency_overrides[get_current_active_user] = lambda: user_b
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/chat/knowledge",
                json={"message": "Probing conversation", "conversation_id": str(conv_a_id)},
            )
            assert resp.status_code == 400
            body = resp.json()
            assert body["success"] is False
            assert "Conversation not found or access denied." in body["message"]
            assert "data" not in body or body["data"] is None
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    @patch("app.api.v1.chat.ChatRepository.get_conversation", new_callable=AsyncMock)
    def test_user_b_cannot_inspect_user_a_chat_history(self, mock_get_conv) -> None:
        """GET /chat/history/{id} returns 404 for another user's conversation."""
        user_b = _create_user("User B")
        conv_a_id = uuid.uuid4()

        mock_get_conv.return_value = []

        app.dependency_overrides[get_current_active_user] = lambda: user_b
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/v1/chat/history/{conv_a_id}")
            assert resp.status_code == 404
            body = resp.json()
            assert body["message"] == "Conversation not found"
            mock_get_conv.assert_called_once_with(conv_a_id, user_id=user_b.id)
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    @patch("app.api.v1.chat.ChatRepository.get_conversation", new_callable=AsyncMock)
    def test_owner_can_retrieve_own_chat_history(self, mock_get_conv) -> None:
        """Owner receives their own messages when retrieving history."""
        user_a = _create_user("User A")
        conv_a_id = uuid.uuid4()

        mock_msg = MagicMock()
        mock_msg.id = uuid.uuid4()
        mock_msg.role = "user"
        mock_msg.content = "User A private query"
        mock_msg.sources = None
        mock_msg.created_at = datetime.now(timezone.utc)
        mock_msg.user_id = user_a.id

        mock_get_conv.return_value = [mock_msg]

        app.dependency_overrides[get_current_active_user] = lambda: user_a
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/v1/chat/history/{conv_a_id}")
            assert resp.status_code == 200
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["total"] == 1
            assert body["data"]["messages"][0]["content"] == "User A private query"
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    @patch("app.api.v1.chat.ChatService.prediction_chat", new_callable=AsyncMock)
    def test_user_b_denied_access_to_user_a_prediction_conversation(self, mock_pred_chat) -> None:
        """User B passing User A's conversation ID to prediction chat receives 400 without data leakage."""
        user_b = _create_user("User B")
        pred_id = uuid.uuid4()
        conv_a_id = uuid.uuid4()

        mock_pred_chat.side_effect = ValueError("Conversation not found or access denied.")

        app.dependency_overrides[get_current_active_user] = lambda: user_b
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.post(
                f"/api/v1/chat/prediction/{pred_id}",
                json={"message": "Probing prediction conversation", "conversation_id": str(conv_a_id)},
            )
            assert resp.status_code == 400
            body = resp.json()
            assert body["success"] is False
            assert "Conversation not found or access denied." in body["message"]
            assert "data" not in body or body["data"] is None
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    @patch("app.api.v1.chat.ChatRepository.get_conversation", new_callable=AsyncMock)
    def test_bidirectional_multi_user_isolation(self, mock_get_conv) -> None:
        """User A and User B cannot access each other's conversations, but can access their own."""
        user_a = _create_user("User A")
        user_b = _create_user("User B")
        conv_a = uuid.uuid4()
        conv_b = uuid.uuid4()

        msg_a = MagicMock(id=uuid.uuid4(), role="user", content="Msg A", sources=None, created_at=datetime.now(timezone.utc), user_id=user_a.id)
        msg_b = MagicMock(id=uuid.uuid4(), role="user", content="Msg B", sources=None, created_at=datetime.now(timezone.utc), user_id=user_b.id)

        # Repository logic respects user_id scoping
        async def fake_get_conv(conv_id: uuid.UUID, user_id: uuid.UUID | None = None, limit: int = 50):
            if conv_id == conv_a and user_id == user_a.id:
                return [msg_a]
            if conv_id == conv_b and user_id == user_b.id:
                return [msg_b]
            return []

        mock_get_conv.side_effect = fake_get_conv

        # 1. User A requests conv_a -> 200 OK
        app.dependency_overrides[get_current_active_user] = lambda: user_a
        app.dependency_overrides[get_db] = lambda: AsyncMock()
        client_a = TestClient(app)
        res_a_own = client_a.get(f"/api/v1/chat/history/{conv_a}")
        assert res_a_own.status_code == 200
        assert res_a_own.json()["data"]["messages"][0]["content"] == "Msg A"

        # 2. User A requests conv_b -> 404 Not Found
        res_a_foreign = client_a.get(f"/api/v1/chat/history/{conv_b}")
        assert res_a_foreign.status_code == 404
        assert res_a_foreign.json()["message"] == "Conversation not found"

        # 3. User B requests conv_b -> 200 OK
        app.dependency_overrides[get_current_active_user] = lambda: user_b
        client_b = TestClient(app)
        res_b_own = client_b.get(f"/api/v1/chat/history/{conv_b}")
        assert res_b_own.status_code == 200
        assert res_b_own.json()["data"]["messages"][0]["content"] == "Msg B"

        # 4. User B requests conv_a -> 404 Not Found
        res_b_foreign = client_b.get(f"/api/v1/chat/history/{conv_a}")
        assert res_b_foreign.status_code == 404
        assert res_b_foreign.json()["message"] == "Conversation not found"

        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# Phase 6.2-B: Chat Input Boundary Hardening Tests
# ==============================================================================


class TestChatInputBoundary:
    """Verifies that empty, whitespace-only, and oversized messages are rejected safely."""

    def test_empty_message_rejected_with_422(self) -> None:
        user = _create_user("User A")
        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.post("/api/v1/chat/knowledge", json={"message": ""})
            assert resp.status_code == 422
            body = resp.json()
            assert body["success"] is False
            assert "validation" in body["message"].lower()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    def test_whitespace_only_message_rejected_with_422(self) -> None:
        user = _create_user("User A")
        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.post("/api/v1/chat/knowledge", json={"message": "   \n\t   "})
            assert resp.status_code == 422
            body = resp.json()
            assert body["success"] is False
            assert any("whitespace" in err["message"].lower() for err in body.get("errors", []))
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    @patch("app.api.v1.chat.ChatService.knowledge_chat", new_callable=AsyncMock)
    def test_message_at_exact_limit_is_accepted(self, mock_know_chat) -> None:
        """Message with exactly 2000 characters is accepted."""
        user = _create_user("User A")
        mock_know_chat.return_value = {
            "response": "Understood.",
            "conversation_id": str(uuid.uuid4()),
            "sources": None,
            "disclaimer": "Test",
        }

        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            exact_msg = "A" * 2000
            resp = client.post("/api/v1/chat/knowledge", json={"message": exact_msg})
            assert resp.status_code == 200
            mock_know_chat.assert_called_once()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    @patch("app.api.v1.chat.ChatService.knowledge_chat", new_callable=AsyncMock)
    def test_oversized_message_rejected_before_service_call(self, mock_know_chat) -> None:
        """Message with 2001 characters is rejected at boundary with 422, never calling ChatService."""
        user = _create_user("User A")
        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            oversized_msg = "A" * 2001
            resp = client.post("/api/v1/chat/knowledge", json={"message": oversized_msg})
            assert resp.status_code == 422
            body = resp.json()
            assert body["success"] is False
            # Crucial invariant: ChatService was never called!
            mock_know_chat.assert_not_called()
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    def test_invalid_conversation_id_rejected_with_422(self) -> None:
        """Invalid conversation UUID string is rejected safely."""
        user = _create_user("User A")
        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/chat/knowledge",
                json={"message": "Valid query", "conversation_id": "not-a-uuid"},
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    def test_invalid_prediction_id_rejected_with_422(self) -> None:
        """Invalid prediction UUID path parameter is rejected safely."""
        user = _create_user("User A")
        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.post(
                "/api/v1/chat/prediction/invalid-uuid",
                json={"message": "Valid query"},
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# Phase 6.2-C: Error & Data Leakage Hardening Tests
# ==============================================================================


class TestErrorAndDataLeakageHardening:
    """Verifies that internal exceptions do not leak sensitive details to API clients."""

    @patch("app.api.v1.summary.LLMSummaryService.generate_summary", new_callable=AsyncMock)
    def test_summary_post_sanitizes_internal_database_exceptions(self, mock_gen) -> None:
        """Database connection error or SQL exception is sanitized in POST /predictions/{id}/summary."""
        user = _create_user("User A")
        pred_id = uuid.uuid4()
        sensitive_db_err = (
            "OperationalError: connection to postgresql://postgres:SuperSecretP@ssword@db.internal:5432/oncovision "
            "failed: FATAL: password authentication failed for user 'postgres' at /app/core/db.py line 42"
        )
        mock_gen.side_effect = RuntimeError(sensitive_db_err)

        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.post(f"/api/v1/predictions/{pred_id}/summary", json={"language": "en"})
            assert resp.status_code == 500
            body = resp.json()
            assert body["success"] is False
            # Safe generic message
            assert body["message"] == "An error occurred while generating the summary. Please try again."
            # Assert absence of sensitive details
            raw_response = resp.text
            assert "SuperSecretP@ssword" not in raw_response
            assert "db.internal" not in raw_response
            assert "OperationalError" not in raw_response
            assert "/app/core/db.py" not in raw_response
            assert "FATAL" not in raw_response
            # Request ID preserved
            assert "request_id" in body
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)

    @patch("app.api.v1.summary.LLMSummaryService.generate_summary", new_callable=AsyncMock)
    def test_summary_get_sanitizes_internal_exceptions(self, mock_gen) -> None:
        """Internal exception is sanitized in GET /predictions/{id}/summary."""
        user = _create_user("User A")
        pred_id = uuid.uuid4()
        gemini_secret_err = "GoogleAPIError: API key AIzaSyFakeKeyInvalid4938 failed for /v1beta/models/gemini-flash"
        mock_gen.side_effect = Exception(gemini_secret_err)

        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: AsyncMock()

        try:
            client = TestClient(app)
            resp = client.get(f"/api/v1/predictions/{pred_id}/summary")
            assert resp.status_code == 500
            body = resp.json()
            assert body["success"] is False
            assert body["message"] == "An error occurred while retrieving the summary. Please try again."
            raw_response = resp.text
            assert "AIzaSyFakeKeyInvalid4938" not in raw_response
            assert "GoogleAPIError" not in raw_response
            assert "request_id" in body
        finally:
            app.dependency_overrides.pop(get_current_active_user, None)
            app.dependency_overrides.pop(get_db, None)


# ==============================================================================
# Phase 6.2-A: Repository Ownership Query Structure Tests
# ==============================================================================


class TestChatRepositoryOwnershipQueries:
    """Verifies that ChatRepository query construction strictly enforces user scoping."""

    def test_get_conversation_applies_user_id_filter_when_provided(self) -> None:
        async def _run() -> None:
            conv_id = uuid.uuid4()
            user_id = uuid.uuid4()
            mock_session = AsyncMock()
            fake_result = MagicMock()
            fake_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=fake_result)

            repo = ChatRepository(mock_session)
            await repo.get_conversation(conv_id, user_id=user_id)

            mock_session.execute.assert_called_once()
            stmt = mock_session.execute.call_args[0][0]
            compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
            assert "chat_messages.conversation_id =" in compiled
            assert "chat_messages.user_id =" in compiled

        asyncio.run(_run())

    def test_get_conversation_omits_user_id_filter_when_none(self) -> None:
        async def _run() -> None:
            conv_id = uuid.uuid4()
            mock_session = AsyncMock()
            fake_result = MagicMock()
            fake_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=fake_result)

            repo = ChatRepository(mock_session)
            await repo.get_conversation(conv_id, user_id=None)

            mock_session.execute.assert_called_once()
            stmt = mock_session.execute.call_args[0][0]
            compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
            assert "chat_messages.conversation_id =" in compiled
            assert "chat_messages.user_id =" not in compiled

        asyncio.run(_run())

    def test_get_conversation_metadata_queries_owner_and_type(self) -> None:
        async def _run() -> None:
            conv_id = uuid.uuid4()
            user_id = uuid.uuid4()
            pred_id = uuid.uuid4()
            mock_session = AsyncMock()

            row = MagicMock(user_id=user_id, chat_type="prediction", prediction_id=pred_id)
            fake_result = MagicMock()
            fake_result.first.return_value = row
            mock_session.execute = AsyncMock(return_value=fake_result)

            repo = ChatRepository(mock_session)
            meta = await repo.get_conversation_metadata(conv_id)

            assert meta == {
                "user_id": user_id,
                "chat_type": "prediction",
                "prediction_id": pred_id,
            }

        asyncio.run(_run())

    def test_get_conversation_owner_returns_user_id(self) -> None:
        async def _run() -> None:
            conv_id = uuid.uuid4()
            user_id = uuid.uuid4()
            mock_session = AsyncMock()

            fake_result = MagicMock()
            fake_result.scalar_one_or_none.return_value = user_id
            mock_session.execute = AsyncMock(return_value=fake_result)

            repo = ChatRepository(mock_session)
            owner = await repo.get_conversation_owner(conv_id)

            assert owner == user_id

        asyncio.run(_run())
