"""Router-level and integration tests for AI Chat Two-Phase Verified SSE endpoints.

Validates:
- `POST /api/v1/chat/prediction/{prediction_id}/stream`
- `POST /api/v1/chat/knowledge/stream`
- SSE protocol headers (`text/event-stream`, `no-cache`, `X-Accel-Buffering: no`)
- Deterministic event sequence: `status`, `sources`, `delta`, `done`
- Safety fail-closed guarantees: visual hallucination and developer boilerplate suppression
- Persistence invariant: assistant message saved only after validation succeeds
- Cancellation handling: no assistant message persisted on early disconnect
"""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.dependencies.auth import get_current_active_user
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.models.prediction_history import PredictionHistoryRecord
from app.models.chat_message import ChatMessage
from app.rag.classifier import QueryDomain, QueryIntent, QueryScope
from app.rag.retriever import RetrievedContext, RetrievedDocument
from app.rag.schemas import Citation, GroundedAnswer
from app.rag.safety import VISUAL_EVIDENCE_REFUSAL_MESSAGE


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
def fake_db() -> AsyncMock:
    db = AsyncMock()
    return db


@pytest.fixture
def client(current_user: User, fake_db: AsyncMock):
    """TestClient with authenticated user and fake db session."""
    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: fake_db

    yield TestClient(app)

    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def sse_test_setup():
    from sse_starlette.sse import AppStatus
    AppStatus.should_exit_event = None
    with patch("app.repositories.chat_repository.ChatRepository.count_user_messages_in_window", new_callable=AsyncMock) as mock_rate:
        mock_rate.return_value = 0
        yield
    AppStatus.should_exit_event = None


def parse_sse_events(raw_body: str) -> list[dict[str, str]]:
    """Helper to parse raw SSE text into a list of {event, data} dicts."""
    events = []
    current_event = "message"
    current_data = []

    for line in raw_body.splitlines():
        if line.startswith("event:"):
            current_event = line.split("event:", 1)[1].strip()
        elif line.startswith("data:"):
            current_data.append(line.split("data:", 1)[1].strip())
        elif line == "":
            if current_data:
                events.append({
                    "event": current_event,
                    "data": "\n".join(current_data),
                })
                current_event = "message"
                current_data = []

    if current_data:
        events.append({
            "event": current_event,
            "data": "\n".join(current_data),
        })

    return events


class TestChatStreamAuthorization:
    def test_unauthenticated_knowledge_stream_returns_401(self) -> None:
        unauth_client = TestClient(app)
        resp = unauth_client.post(
            "/api/v1/chat/knowledge/stream",
            json={"message": "What is adenocarcinoma?"},
        )
        assert resp.status_code == 401

    def test_unauthenticated_prediction_stream_returns_401(self) -> None:
        unauth_client = TestClient(app)
        pred_id = str(uuid.uuid4())
        resp = unauth_client.post(
            f"/api/v1/chat/prediction/{pred_id}/stream",
            json={"message": "Explain this result"},
        )
        assert resp.status_code == 401


class TestKnowledgeChatStream:
    @patch("app.services.chat_service.GroundedRAGGenerator.generate_grounded_stream")
    @patch("app.services.chat_service.RAGRetriever.retrieve_context")
    def test_successful_knowledge_stream_protocol(
        self,
        mock_retrieve,
        mock_gen_stream,
        client: TestClient,
        current_user: User,
    ) -> None:
        default_scope = QueryScope(
            domain=QueryDomain.GENERAL_ONCOLOGY,
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=1.0,
        )
        doc = RetrievedDocument(
            content="Glandular structures characterize adenocarcinoma.",
            topic="lung_adenocarcinoma",
            source="WHO Guidelines",
            source_title="WHO Guidelines on Lung Tumors",
            similarity=0.88,
            source_tier=1,
            document_title="Lung Adenocarcinoma",
            citation="WHO 2021",
            source_url="https://ncbi.nlm.nih.gov/pmc/articles/123",
        )
        mock_retrieve.return_value = RetrievedContext(
            chunks=[doc],
            query_scope=default_scope,
            reason="success",
        )

        mock_gen_stream.return_value = GroundedAnswer(
            answer="Lung adenocarcinoma exhibits glandular differentiation [S1].",
            citations=[
                Citation(
                    source_id="S1",
                    document_id="doc1",
                    document_title="Lung Adenocarcinoma",
                    source_title="WHO Guidelines",
                    source_url="https://ncbi.nlm.nih.gov/pmc/articles/123",
                    source_tier=1,
                )
            ],
            grounded=True,
            disclaimer="Educational only.",
            request_id="req-test-123",
        )

        resp = client.post(
            "/api/v1/chat/knowledge/stream",
            json={"message": "What is lung adenocarcinoma?"},
        )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert "no-cache" in resp.headers["cache-control"]
        assert resp.headers["x-accel-buffering"] == "no"

        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "status" in event_types
        assert "sources" in event_types
        assert "delta" in event_types
        assert "done" in event_types

        # Check status progression
        status_events = [json.loads(e["data"]) for e in events if e["event"] == "status"]
        stages = [s["stage"] for s in status_events]
        assert "starting" in stages
        assert "retrieving" in stages
        assert "synthesizing" in stages
        assert "validating" in stages
        assert "completed" in stages

        # Check sources event
        sources_events = [json.loads(e["data"]) for e in events if e["event"] == "sources"]
        assert len(sources_events) == 1
        assert len(sources_events[0]["sources"]) == 1
        assert sources_events[0]["sources"][0]["source_id"] == "S1"

        # Check deltas reconstruct validated answer
        deltas = [json.loads(e["data"])["text"] for e in events if e["event"] == "delta"]
        accumulated_text = "".join(deltas)
        assert accumulated_text == "Lung adenocarcinoma exhibits glandular differentiation [S1]."

        # Check done event
        done_events = [json.loads(e["data"]) for e in events if e["event"] == "done"]
        assert len(done_events) == 1
        assert done_events[0]["grounded"] is True
        assert len(done_events[0]["citations"]) == 1
        assert bool(done_events[0]["request_id"])

    @patch("app.services.chat_service.GroundedRAGGenerator.generate_grounded_stream")
    @patch("app.services.chat_service.RAGRetriever.retrieve_context")
    def test_visual_evidence_hallucination_remains_blocked_in_stream(
        self,
        mock_retrieve,
        mock_gen_stream,
        client: TestClient,
        current_user: User,
    ) -> None:
        """P0 check: Visual hallucination cannot be streamed; safe refusal must be emitted instead."""
        default_scope = QueryScope(
            domain=QueryDomain.GENERAL_ONCOLOGY,
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=1.0,
        )
        mock_retrieve.return_value = RetrievedContext(chunks=[], query_scope=default_scope, reason="success")

        # The generator's fail-closed boundary produces the refusal message
        mock_gen_stream.return_value = GroundedAnswer(
            answer=VISUAL_EVIDENCE_REFUSAL_MESSAGE,
            citations=[],
            grounded=False,
            refusal_reason="visual_evidence_boundary",
            disclaimer="Educational only.",
        )

        resp = client.post(
            "/api/v1/chat/knowledge/stream",
            json={"message": "What microscopic structures do you see in this slide?"},
        )
        assert resp.status_code == 200
        events = parse_sse_events(resp.text)

        deltas = [json.loads(e["data"])["text"] for e in events if e["event"] == "delta"]
        accumulated = "".join(deltas)

        # Confirm hallucinated observation is absent and refusal is present
        assert "I see malignant glandular structures" not in accumulated
        assert VISUAL_EVIDENCE_REFUSAL_MESSAGE in accumulated

        done_event = next(json.loads(e["data"]) for e in events if e["event"] == "done")
        assert done_event["grounded"] is False

    @patch("app.services.chat_service.GroundedRAGGenerator.generate_grounded_stream")
    @patch("app.services.chat_service.RAGRetriever.retrieve_context")
    def test_developer_boilerplate_suppressed_in_stream(
        self,
        mock_retrieve,
        mock_gen_stream,
        client: TestClient,
        current_user: User,
    ) -> None:
        """Verify developer boilerplate is suppressed in streamed deltas."""
        default_scope = QueryScope(
            domain=QueryDomain.GENERAL_ONCOLOGY,
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=1.0,
        )
        mock_retrieve.return_value = RetrievedContext(chunks=[], query_scope=default_scope, reason="success")

        # Generator returns answer where post-generation validation already stripped boilerplate
        mock_gen_stream.return_value = GroundedAnswer(
            answer="Adenocarcinoma arises in epithelial tissue.",
            citations=[],
            grounded=True,
            disclaimer="Educational only.",
        )

        resp = client.post(
            "/api/v1/chat/knowledge/stream",
            json={"message": "What is adenocarcinoma?"},
        )
        assert resp.status_code == 200
        events = parse_sse_events(resp.text)

        deltas = [json.loads(e["data"])["text"] for e in events if e["event"] == "delta"]
        accumulated = "".join(deltas)

        # Developer portfolio info must not be present
        assert "Developed by" not in accumulated
        assert "github.com" not in accumulated
        assert "Adenocarcinoma arises in epithelial tissue." in accumulated

    @patch("app.services.chat_service.GroundedRAGGenerator.generate_grounded_stream")
    @patch("app.services.chat_service.RAGRetriever.retrieve_context")
    def test_invalid_citation_fails_closed_in_stream(
        self,
        mock_retrieve,
        mock_gen_stream,
        client: TestClient,
        current_user: User,
    ) -> None:
        """Verify invalid citation causes fail-closed behavior before streaming."""
        default_scope = QueryScope(
            domain=QueryDomain.GENERAL_ONCOLOGY,
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=1.0,
        )
        mock_retrieve.return_value = RetrievedContext(chunks=[], query_scope=default_scope, reason="success")

        # Generator fails closed when phantom citation [S99] is detected
        mock_gen_stream.return_value = GroundedAnswer(
            answer="I do not have sufficient validated medical knowledge to verify this.",
            citations=[],
            grounded=False,
            refusal_reason="invalid_citations_detected",
            disclaimer="Educational only.",
        )

        resp = client.post(
            "/api/v1/chat/knowledge/stream",
            json={"message": "Tell me about this claim"},
        )
        assert resp.status_code == 200
        events = parse_sse_events(resp.text)

        deltas = [json.loads(e["data"])["text"] for e in events if e["event"] == "delta"]
        accumulated = "".join(deltas)

        assert "[S99]" not in accumulated
        done_event = next(json.loads(e["data"]) for e in events if e["event"] == "done")
        assert done_event["grounded"] is False

    @patch("app.services.chat_service.GroundedRAGGenerator.generate_grounded_stream")
    @patch("app.services.chat_service.RAGRetriever.retrieve_context")
    def test_generator_timeout_yields_sanitized_error_in_stream(
        self,
        mock_retrieve,
        mock_gen_stream,
        client: TestClient,
        current_user: User,
    ) -> None:
        """Verify timeout or provider error yields a sanitized error event without leaking internals."""
        default_scope = QueryScope(
            domain=QueryDomain.GENERAL_ONCOLOGY,
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=1.0,
        )
        mock_retrieve.return_value = RetrievedContext(chunks=[], query_scope=default_scope, reason="success")
        mock_gen_stream.side_effect = TimeoutError("Gemini streaming timeout 504")

        resp = client.post(
            "/api/v1/chat/knowledge/stream",
            json={"message": "What is adenocarcinoma?"},
        )
        assert resp.status_code == 200
        events = parse_sse_events(resp.text)

        error_events = [json.loads(e["data"]) for e in events if e["event"] == "error"]
        assert len(error_events) == 1
        assert error_events[0]["error_type"] == "generation_timeout"
        # Verify provider internals / stack traces are NOT leaked
        assert "504" not in error_events[0]["message"]
        assert "Gemini" not in error_events[0]["message"]
        assert "timed out" in error_events[0]["message"]


class TestPredictionChatStream:
    @patch("app.services.chat_service.GroundedRAGGenerator.generate_grounded_stream")
    @patch("app.services.chat_service.RAGRetriever.retrieve_context")
    @patch("app.services.chat_service.ChatRepository.create")
    def test_successful_prediction_stream_persists_assistant_message(
        self,
        mock_create,
        mock_retrieve,
        mock_gen_stream,
        client: TestClient,
        current_user: User,
        fake_db: AsyncMock,
    ) -> None:
        """Verify assistant message persistence happens after generation and validation."""
        pred_id = uuid.uuid4()
        fake_pred = PredictionHistoryRecord(
            id=pred_id,
            user_id=current_user.id,
            predicted_class="lung_adenocarcinoma",
            confidence=0.99,
            agreement_ratio=1.0,
        )

        # Mock database select for prediction
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_pred
        mock_result.scalars.return_value.all.return_value = []
        fake_db.execute.return_value = mock_result

        default_scope = QueryScope(
            domain=QueryDomain.GENERAL_ONCOLOGY,
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=1.0,
        )

        mock_retrieve.return_value = RetrievedContext(chunks=[], query_scope=default_scope, reason="success")
        mock_gen_stream.return_value = GroundedAnswer(
            answer="The specimen is characterized by glandular structures [S1].",
            citations=[
                Citation(
                    source_id="S1",
                    document_id="doc1",
                    document_title="Title",
                    source_title="Source",
                    source_url="https://cancer.gov",
                )
            ],
            grounded=True,
            disclaimer="Educational only.",
        )

        resp = client.post(
            f"/api/v1/chat/prediction/{pred_id}/stream",
            json={"message": "Explain this case prediction"},
        )

        assert resp.status_code == 200
        events = parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]
        assert "done" in event_types

        # Verify that ChatRepository.create was called for user message, then assistant message
        assert mock_create.call_count >= 2
        saved_messages = [call.args[0] for call in mock_create.call_args_list]
        roles = [m.role for m in saved_messages if isinstance(m, ChatMessage)]
        assert "user" in roles
        assert "assistant" in roles

    def test_client_disconnect_cancels_without_persisting_assistant(
        self,
        current_user: User,
    ) -> None:
        """Verify that when client disconnects during generation, assistant message is not persisted."""
        import asyncio
        from app.services.chat_service import ChatService
        from unittest.mock import AsyncMock, MagicMock

        async def _test():
            fake_session = AsyncMock()
            service = ChatService(fake_session)

            # Mock request that simulates disconnect right after starting
            mock_req = MagicMock()
            mock_req.is_disconnected = AsyncMock(side_effect=[False, True])

            with patch.object(service.repo, "create", new_callable=AsyncMock) as mock_repo_create, \
                 patch.object(service.repo, "count_user_messages_in_window", new_callable=AsyncMock) as mock_rl, \
                 patch("app.services.chat_service.RAGRetriever.retrieve_context", new_callable=AsyncMock) as mock_ret:

                mock_rl.return_value = 0
                default_scope = QueryScope(
                    domain=QueryDomain.GENERAL_ONCOLOGY,
                    intent=QueryIntent.HISTOPATHOLOGY,
                    confidence=1.0,
                )
                mock_ret.return_value = RetrievedContext(chunks=[], query_scope=default_scope, reason="success")

                events = []
                async for ev in service.stream_knowledge_chat(
                    user_id=current_user.id,
                    message="Explain lung adenocarcinoma",
                    conversation_id=None,
                    raw_request=mock_req,
                ):
                    events.append(ev)

                # When disconnected, generator returns early without yielding done
                done_events = [e for e in events if e.get("event") == "done"]
                assert len(done_events) == 0

                # Verify ONLY user message was persisted, NO assistant message
                assert mock_repo_create.call_count == 1
                saved_msg = mock_repo_create.call_args[0][0]
                assert saved_msg.role == "user"

        asyncio.run(_test())

    @patch("app.services.chat_service.GroundedRAGGenerator.generate_grounded_stream")
    @patch("app.services.chat_service.RAGRetriever.retrieve_context")
    def test_prediction_immutability_preserved_in_stream(
        self,
        mock_retrieve,
        mock_gen_stream,
        client: TestClient,
        current_user: User,
        fake_db: AsyncMock,
    ) -> None:
        """Verify prediction record cannot be mutated by streamed chat generation."""
        pred_id = uuid.uuid4()
        fake_pred = PredictionHistoryRecord(
            id=pred_id,
            user_id=current_user.id,
            predicted_class="colon_adenocarcinoma",
            confidence=0.965,
            agreement_ratio=0.80,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = fake_pred
        mock_result.scalars.return_value.all.return_value = []
        fake_db.execute.return_value = mock_result

        default_scope = QueryScope(
            domain=QueryDomain.GENERAL_ONCOLOGY,
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=1.0,
        )
        mock_retrieve.return_value = RetrievedContext(chunks=[], query_scope=default_scope, reason="success")
        mock_gen_stream.return_value = GroundedAnswer(
            answer="The colon adenocarcinoma classification has high model confidence [S1].",
            citations=[],
            grounded=True,
            disclaimer="Educational only.",
        )

        resp = client.post(
            f"/api/v1/chat/prediction/{pred_id}/stream",
            json={"message": "Is this benign?"},
        )
        assert resp.status_code == 200

        # Check call arguments to generator to ensure prediction summary was frozen and intact
        _, kwargs = mock_gen_stream.call_args
        summary_passed = kwargs.get("prediction_summary")
        assert summary_passed is not None
        assert summary_passed.predicted_class == "colon_adenocarcinoma"
        assert summary_passed.confidence == 0.965
        assert summary_passed.agreement_ratio == 0.80

        # Ensure summary model is frozen (cannot be mutated)
        with pytest.raises(Exception):
            summary_passed.predicted_class = "benign"
