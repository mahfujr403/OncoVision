"""Tests for Phase 5.2 Production Observability, Telemetry & Reliability.

Verifies:
1. Request Correlation ID generation, sanitization, and propagation.
2. Privacy enforcement: ZERO logging of API keys, JWTs, DB URLs, base64 images, or raw queries.
3. Deterministic safety refusal telemetry (skips Gemini, logs rag_safety_refusal).
4. Retrieval observability (rag_retrieval_completed, rag_retrieval_empty, error handling).
5. Grounding decision observability (rag_grounding_accepted, rag_grounding_rejected, skips Gemini).
6. Generation reliability & error classification (rag_generation_started/completed, timeout, api error).
7. Citation validation telemetry (provenance mapping, unsupported citation stripping).
8. Monotonic latency breakdown across all pipeline stages.
9. In-process RAG metrics collector snapshots.
10. Health & readiness endpoints (liveness vs. readiness).
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.history.summary import PredictionHistorySummary
from app.rag.classifier import QueryDomain, QueryIntent, QueryScope, QueryScopeClassifier
from app.rag.generator import GroundedRAGGenerator
from app.rag.observability import (
    EVENT_CITATION_VALIDATION,
    EVENT_GENERATION_COMPLETED,
    EVENT_GENERATION_FAILED,
    EVENT_GENERATION_STARTED,
    EVENT_GENERATION_TIMEOUT,
    EVENT_GROUNDING_ACCEPTED,
    EVENT_GROUNDING_REJECTED,
    EVENT_REQUEST_COMPLETED,
    EVENT_REQUEST_STARTED,
    EVENT_RETRIEVAL_COMPLETED,
    EVENT_RETRIEVAL_EMPTY,
    EVENT_SAFETY_REFUSAL,
    RAGErrorCategory,
    RAGMetricsCollector,
    RAGTelemetryContext,
    default_rag_metrics_collector,
    log_rag_event,
    sanitize_log_data,
    sanitize_request_id,
)
from app.rag.retriever import RAGRetriever, RetrievedContext, RetrievedDocument
from app.rag.safety import SafetyBoundary, SafetyEvaluator
from app.rag.schemas import GroundedAnswer


def make_doc(
    doc_id: str,
    title: str,
    content: str,
    domain: str,
    url: str,
    similarity: float = 0.92,
    tier: int = 2,
) -> RetrievedDocument:
    return RetrievedDocument(
        content=content,
        source=f"{domain}/{doc_id}.md",
        topic=domain,
        similarity=similarity,
        document_id=doc_id,
        document_title=title,
        domain=domain,
        source_title=title,
        source_url=url,
        source_tier=tier,
    )


class TestRequestCorrelation:
    """Verifies correlation ID generation, validation, and propagation."""

    def test_sanitize_request_id_generates_on_none(self):
        req_id = sanitize_request_id(None)
        assert req_id is not None
        assert len(req_id) == 12

    def test_sanitize_request_id_accepts_valid_id(self):
        valid_id = "req-12345-abc_XYZ"
        assert sanitize_request_id(valid_id) == valid_id

    def test_sanitize_request_id_rejects_malformed_and_generates_safe(self):
        # Disallow injection characters or spaces
        malformed = "req; DROP TABLE users; --"
        sanitized = sanitize_request_id(malformed)
        assert sanitized != malformed
        assert len(sanitized) == 12

    def test_request_id_propagated_to_grounded_answer(self):
        async def _run():
            scope = QueryScope(domain=QueryDomain.LUNG, confidence=0.9, intent=QueryIntent.HISTOPATHOLOGY)
            context = RetrievedContext(
                chunks=[make_doc("doc_1", "Lung Pathology", "Glandular formation [S1].", "lung", "https://example.com/lung")],
                query_scope=scope,
            )
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(return_value="Adenocarcinoma features glandular formation [S1].")
            generator = GroundedRAGGenerator(llm_client=mock_client)

            custom_id = "trace-test-uuid-42"
            ans = await generator.generate_grounded_answer("query text", context, request_id=custom_id)

            assert ans.request_id == custom_id
            assert ans.grounded is True

        asyncio.run(_run())


class TestPrivacyAndSensitiveDataRules:
    """Verifies that secrets, tokens, credentials, base64 images, and raw queries are NOT logged."""

    def test_api_key_redacted_from_log_payload(self):
        payload = {
            "api_key": "AIzaSyDummySecretKeyForTest1234567890",
            "message": "AIzaSyDummySecretKeyForTest1234567890 leaked in message",
        }
        sanitized = sanitize_log_data(payload)
        assert sanitized["api_key"] == "[REDACTED]"
        assert "AIzaSy" not in str(sanitized)

    def test_jwt_token_redacted_from_log_payload(self):
        fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature"
        payload = {
            "auth_token": fake_jwt,
            "authorization": f"Bearer {fake_jwt}",
        }
        sanitized = sanitize_log_data(payload)
        assert sanitized["auth_token"] == "[REDACTED]"
        assert sanitized["authorization"] == "[REDACTED]"

    def test_database_url_credentials_redacted(self):
        payload = {
            "database_url": "postgresql+asyncpg://admin_user:super_secret_pw@db.prod.internal:5432/oncovision",
            "error_detail": "connection to postgresql://postgres:mypassword@localhost:5432/onco failed",
        }
        sanitized = sanitize_log_data(payload)
        assert sanitized["database_url"] == "[REDACTED]"
        assert "super_secret_pw" not in str(sanitized)
        assert "mypassword" not in str(sanitized)

    def test_base64_image_data_redacted(self):
        fake_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        payload = {
            "image": fake_b64,
        }
        sanitized = sanitize_log_data(payload)
        assert fake_b64 not in str(sanitized)
        assert "[BASE64_IMAGE_REDACTED]" in sanitized["image"]

    def test_raw_user_query_omitted_by_default(self):
        # Default setting: RAG_LOG_QUERY_CONTENT=False
        payload = {
            "query": "Patient John Doe has severe hemoptysis and suspected stage 4 lung cancer.",
        }
        sanitized = sanitize_log_data(payload)
        assert "query" not in sanitized
        assert sanitized["query_length"] == len("Patient John Doe has severe hemoptysis and suspected stage 4 lung cancer.")
        assert "John Doe" not in str(sanitized)


class TestSafetyObservability:
    """Verifies that safety refusals emit rag_safety_refusal and NEVER call Gemini."""

    def test_diagnosis_refusal_emits_event_and_skips_gemini(self):
        async def _run():
            telemetry = RAGTelemetryContext(request_id="safety-diag-01", chat_type="direct", query="Do I have cancer?")
            mock_client = MagicMock()
            generator = GroundedRAGGenerator(llm_client=mock_client)

            context = RetrievedContext(
                chunks=[],
                query_scope=QueryScope(domain=None, confidence=0.0, intent=QueryIntent.GENERAL_KNOWLEDGE),
            )

            ans = await generator.generate_grounded_answer(
                query="Do I have lung cancer?",
                context=context,
                telemetry=telemetry,
            )

            assert ans.grounded is False
            assert ans.refusal_reason == SafetyBoundary.DIAGNOSIS.value
            mock_client.generate.assert_not_called()

            # Verify events
            event_names = [e["event"] for e in telemetry.events]
            assert EVENT_REQUEST_STARTED in event_names
            assert EVENT_SAFETY_REFUSAL in event_names
            assert EVENT_REQUEST_COMPLETED in event_names
            assert EVENT_GENERATION_STARTED not in event_names
            assert EVENT_GENERATION_COMPLETED not in event_names

            safety_event = next(e for e in telemetry.events if e["event"] == EVENT_SAFETY_REFUSAL)
            assert safety_event["skipped_gemini"] is True
            assert safety_event["boundary"] == SafetyBoundary.DIAGNOSIS.value

        asyncio.run(_run())

    def test_treatment_refusal_emits_event_and_skips_gemini(self):
        async def _run():
            telemetry = RAGTelemetryContext(request_id="safety-tx-02", chat_type="direct", query="What chemo should I take?")
            mock_client = MagicMock()
            generator = GroundedRAGGenerator(llm_client=mock_client)

            context = RetrievedContext(
                chunks=[],
                query_scope=QueryScope(domain=None, confidence=0.0, intent=QueryIntent.TREATMENT),
            )

            ans = await generator.generate_grounded_answer(
                query="What chemotherapy should I personally take for my tumor?",
                context=context,
                telemetry=telemetry,
            )

            assert ans.grounded is False
            assert ans.refusal_reason == SafetyBoundary.TREATMENT.value
            mock_client.generate.assert_not_called()

            event_names = [e["event"] for e in telemetry.events]
            assert EVENT_SAFETY_REFUSAL in event_names
            assert EVENT_GENERATION_STARTED not in event_names

        asyncio.run(_run())


class TestRetrievalObservability:
    """Verifies retrieval telemetry events for success, empty, and failures."""

    def test_empty_query_retrieval_telemetry(self):
        async def _run():
            telemetry = RAGTelemetryContext(request_id="ret-empty-01", query="")
            session = AsyncMock()
            emb_svc = AsyncMock()
            retriever = RAGRetriever(session=session, embedding_service=emb_svc)

            ctx = await retriever.retrieve_context(query="   ", telemetry=telemetry)
            assert ctx.reason == "empty_query"
            assert len(ctx.chunks) == 0

            empty_event = next((e for e in telemetry.events if e["event"] == EVENT_RETRIEVAL_EMPTY), None)
            assert empty_event is not None
            assert empty_event["reason"] == "empty_query"
            assert "retrieval_ms" in empty_event

        asyncio.run(_run())

    def test_embedding_error_retrieval_telemetry(self):
        async def _run():
            telemetry = RAGTelemetryContext(request_id="ret-emb-fail-02", query="lung cancer")
            session = AsyncMock()
            session.scalar.return_value = "record_1"

            emb_svc = AsyncMock()
            emb_svc.get_embedding.side_effect = RuntimeError("Embedding service unavailable")
            retriever = RAGRetriever(session=session, embedding_service=emb_svc)

            ctx = await retriever.retrieve_context(query="lung cancer", telemetry=telemetry)
            assert ctx.reason == "embedding_generation_failed"

            empty_event = next((e for e in telemetry.events if e["event"] == EVENT_RETRIEVAL_EMPTY), None)
            assert empty_event is not None
            assert empty_event["error_category"] == RAGErrorCategory.EMBEDDING_ERROR.value

        asyncio.run(_run())


class TestGroundingObservability:
    """Verifies that grounding rejection emits rag_grounding_rejected and skips Gemini."""

    def test_grounding_rejection_on_weak_similarity(self):
        async def _run():
            telemetry = RAGTelemetryContext(request_id="grounding-weak-01", query="lung adenocarcinoma")
            mock_client = MagicMock()
            generator = GroundedRAGGenerator(llm_client=mock_client)

            scope = QueryScope(domain=QueryDomain.LUNG, confidence=0.8, intent=QueryIntent.HISTOPATHOLOGY)
            context = RetrievedContext(
                chunks=[make_doc("doc_weak", "Weak Match", "Some text", "lung", "https://url.com", similarity=0.62)],
                query_scope=scope,
            )

            ans = await generator.generate_grounded_answer(
                query="lung adenocarcinoma",
                context=context,
                telemetry=telemetry,
            )

            assert ans.grounded is False
            assert ans.refusal_reason == "insufficient_similarity"
            mock_client.generate.assert_not_called()

            event_names = [e["event"] for e in telemetry.events]
            assert EVENT_GROUNDING_REJECTED in event_names
            assert EVENT_GENERATION_STARTED not in event_names

            rejected_event = next(e for e in telemetry.events if e["event"] == EVENT_GROUNDING_REJECTED)
            assert rejected_event["skipped_gemini"] is True
            assert rejected_event["decision_reason"] == "insufficient_similarity"

        asyncio.run(_run())

    def test_grounding_accepted_on_strong_evidence(self):
        async def _run():
            telemetry = RAGTelemetryContext(request_id="grounding-accept-02", query="What is lung adenocarcinoma?")
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(return_value="Lung adenocarcinoma is a carcinoma [S1].")
            generator = GroundedRAGGenerator(llm_client=mock_client)

            scope = QueryScope(domain=QueryDomain.LUNG, confidence=0.95, intent=QueryIntent.GENERAL_KNOWLEDGE)
            context = RetrievedContext(
                chunks=[make_doc("doc_strong", "Lung Adeno", "Morphologic patterns [S1].", "lung", "https://url.com", similarity=0.92)],
                query_scope=scope,
            )

            ans = await generator.generate_grounded_answer(
                query="What is lung adenocarcinoma?",
                context=context,
                telemetry=telemetry,
            )

            assert ans.grounded is True
            mock_client.generate.assert_called_once()

            event_names = [e["event"] for e in telemetry.events]
            assert EVENT_GROUNDING_ACCEPTED in event_names
            assert EVENT_GENERATION_STARTED in event_names
            assert EVENT_GENERATION_COMPLETED in event_names
            assert EVENT_CITATION_VALIDATION in event_names

        asyncio.run(_run())


class TestGenerationReliabilityAndErrors:
    """Verifies timeout handling, API error handling, and citation validation events."""

    def test_gemini_generation_timeout_telemetry(self):
        async def _run():
            telemetry = RAGTelemetryContext(request_id="gen-timeout-01", query="histology query")

            async def _slow_generate(*args, **kwargs):
                await asyncio.sleep(2.0)
                return "Never returned"

            mock_client = MagicMock()
            mock_client.generate = AsyncMock(side_effect=_slow_generate)
            generator = GroundedRAGGenerator(llm_client=mock_client)
            generator.settings.RAG_GENERATION_TIMEOUT = 0.05  # Force quick timeout

            scope = QueryScope(domain=QueryDomain.LUNG, confidence=0.9, intent=QueryIntent.HISTOPATHOLOGY)
            context = RetrievedContext(
                chunks=[make_doc("doc_1", "Lung Path", "Glandular features.", "lung", "https://url.com", similarity=0.90)],
                query_scope=scope,
            )

            ans = await generator.generate_grounded_answer("histology query", context, telemetry=telemetry)

            assert ans.grounded is False
            assert ans.refusal_reason == "generation_timeout"
            assert "timed out" in ans.answer.lower()

            timeout_event = next((e for e in telemetry.events if e["event"] == EVENT_GENERATION_TIMEOUT), None)
            assert timeout_event is not None
            assert timeout_event["error_category"] == RAGErrorCategory.GENERATION_TIMEOUT.value

        asyncio.run(_run())

    def test_gemini_generation_api_failure_telemetry(self):
        async def _run():
            telemetry = RAGTelemetryContext(request_id="gen-fail-02", query="histology query")

            mock_client = MagicMock()
            mock_client.generate = AsyncMock(side_effect=RuntimeError("Google 503 Backend Service Unavailable"))
            generator = GroundedRAGGenerator(llm_client=mock_client)

            scope = QueryScope(domain=QueryDomain.LUNG, confidence=0.9, intent=QueryIntent.HISTOPATHOLOGY)
            context = RetrievedContext(
                chunks=[make_doc("doc_1", "Lung Path", "Glandular features.", "lung", "https://url.com", similarity=0.90)],
                query_scope=scope,
            )

            ans = await generator.generate_grounded_answer("histology query", context, telemetry=telemetry)

            assert ans.grounded is False
            assert ans.refusal_reason == "api_error"
            assert "error occurred while generating" in ans.answer

            failed_event = next((e for e in telemetry.events if e["event"] == EVENT_GENERATION_FAILED), None)
            assert failed_event is not None
            assert failed_event["error_category"] == RAGErrorCategory.GENERATION_API_ERROR.value

        asyncio.run(_run())

    def test_citation_validation_strips_unsupported_sources(self):
        async def _run():
            telemetry = RAGTelemetryContext(request_id="cit-strip-03", query="Explain pathology")

            # LLM cites [S1] which exists, and hallucinates [S99] which does not exist
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="Adenocarcinoma exhibits acinar growth [S1] and imaginary features [S99]."
            )
            generator = GroundedRAGGenerator(llm_client=mock_client)

            scope = QueryScope(domain=QueryDomain.LUNG, confidence=0.9, intent=QueryIntent.HISTOPATHOLOGY)
            context = RetrievedContext(
                chunks=[make_doc("doc_1", "Lung Path", "Acinar growth pattern.", "lung", "https://url.com", similarity=0.92)],
                query_scope=scope,
            )

            ans = await generator.generate_grounded_answer("Explain pathology", context, telemetry=telemetry)

            assert ans.grounded is True
            assert len(ans.citations) == 1
            assert ans.citations[0].source_id == "S1"
            assert "[S99]" not in ans.answer

            cit_event = next((e for e in telemetry.events if e["event"] == EVENT_CITATION_VALIDATION), None)
            assert cit_event is not None
            assert cit_event["total_citations_found"] == 2
            assert cit_event["valid_citations_count"] == 1
            assert cit_event["unsupported_citations_stripped"] == 1

        asyncio.run(_run())


class TestLatencyBreakdownAndMetricsCollector:
    """Verifies that monotonic latencies are tracked and metrics collector works."""

    def test_latency_breakdown_presence(self):
        async def _run():
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(return_value="Valid answer [S1].")
            generator = GroundedRAGGenerator(llm_client=mock_client)

            scope = QueryScope(domain=QueryDomain.LUNG, confidence=0.9, intent=QueryIntent.HISTOPATHOLOGY)
            context = RetrievedContext(
                chunks=[make_doc("doc_1", "Doc 1", "Content [S1]", "lung", "https://url.com", similarity=0.91)],
                query_scope=scope,
                classification_latency_ms=0.5,
                retrieval_latency_ms=12.4,
            )

            ans = await generator.generate_grounded_answer("query", context)

            assert ans.latencies is not None
            assert "classification_ms" in ans.latencies
            assert "safety_ms" in ans.latencies
            assert "retrieval_ms" in ans.latencies
            assert "grounding_ms" in ans.latencies
            assert "generation_ms" in ans.latencies
            assert "citation_validation_ms" in ans.latencies
            assert "total_latency_ms" in ans.latencies

            assert ans.latencies["retrieval_ms"] == 12.4
            assert ans.latencies["total_latency_ms"] >= ans.latencies["generation_ms"]

        asyncio.run(_run())

    def test_rag_metrics_collector_snapshot(self):
        collector = RAGMetricsCollector()
        collector.record_event(EVENT_REQUEST_STARTED, {})
        collector.record_event(EVENT_SAFETY_REFUSAL, {})
        collector.record_event(EVENT_GROUNDING_REJECTED, {})
        collector.record_event(EVENT_RETRIEVAL_EMPTY, {})
        collector.record_event(EVENT_GENERATION_FAILED, {})
        collector.record_event(EVENT_REQUEST_COMPLETED, {"total_latency_ms": 100.0, "grounded": False})

        snapshot = collector.snapshot()
        assert snapshot.rag_requests_total == 1
        assert snapshot.rag_safety_refusals_total == 1
        assert snapshot.rag_grounding_rejections_total == 1
        assert snapshot.rag_retrieval_empty_total == 1
        assert snapshot.rag_generation_failures_total == 1
        assert snapshot.average_request_latency_ms == 100.0


class TestHealthAndReadinessProbes:
    """Verifies that health and readiness endpoints distinguish liveness and readiness."""

    def test_liveness_endpoint_returns_healthy(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"

    def test_readiness_endpoint_checks_database_without_llm(self):
        from fastapi.testclient import TestClient
        from app.main import app

        with patch("app.api.v1.health.check_readiness", new_callable=AsyncMock) as mock_ready:
            mock_ready.return_value = {"database": "connected", "pgvector": "available"}
            client = TestClient(app)
            resp = client.get("/api/v1/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["status"] == "ready"
            assert data["data"]["database"] == "connected"
            assert data["data"]["pgvector"] == "available"
