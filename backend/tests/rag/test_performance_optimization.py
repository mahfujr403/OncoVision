"""Unit and regression tests for Phase 5.3: Production RAG Performance & Cost Optimization.

Covers:
- QueryEmbeddingCache (normalization, SHA-256 privacy, TTL, LRU eviction, stats)
- EmbeddingService cache integration
- Safety short-circuit optimization (0 embedding calls, 0 DB queries on direct safety refusals)
- Database column projection (load_only) and one-time record check
- Gemini client error classification (retryable vs non-retryable fast-fail)
"""

from __future__ import annotations

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import GeminiClient, is_retryable_llm_error
from app.models.knowledge_embedding import KnowledgeEmbedding
from app.rag.cache import QueryEmbeddingCache
from app.rag.classifier import QueryDomain, QueryIntent, QueryScope, QueryScopeClassifier
from app.rag.embeddings import EmbeddingService
from app.rag.generator import GroundedRAGGenerator
from app.rag.observability import RAGTelemetryContext
from app.rag.retriever import RAGRetriever, RetrievedDocument
from app.rag.safety import SafetyBoundary, SafetyEvaluator
from app.services.chat_service import ChatService


# ==============================================================================
# 1. QueryEmbeddingCache Tests
# ==============================================================================


class TestQueryEmbeddingCache:
    """Test suite for thread-safe, bounded, privacy-preserving in-process embedding cache."""

    def test_cache_hit_and_miss(self) -> None:
        """Verify cache returns None on miss and cached vector on hit."""
        cache = QueryEmbeddingCache(max_size=10, ttl_seconds=60.0)
        vec = [0.1] * 768

        assert cache.get("What is lung adenocarcinoma?") is None

        cache.set("What is lung adenocarcinoma?", vec)
        cached = cache.get("What is lung adenocarcinoma?")
        assert cached == vec

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_query_normalization(self) -> None:
        """Verify normalization ignores whitespace and casing."""
        cache = QueryEmbeddingCache(max_size=10, ttl_seconds=60.0)
        vec = [0.2] * 768

        cache.set("  What   IS  Colon   Adenocarcinoma?  ", vec)
        # Look up with different casing and single whitespace
        cached = cache.get("what is colon adenocarcinoma?")
        assert cached == vec

    def test_sha256_hash_privacy(self) -> None:
        """Verify raw query text is never stored in cache dictionary keys."""
        cache = QueryEmbeddingCache(max_size=10, ttl_seconds=60.0)
        raw_query = "Sensitive clinical query regarding patient mutation status"
        vec = [0.3] * 768

        cache.set(raw_query, vec)
        # Ensure raw query text is nowhere in cache keys
        for key in cache._cache.keys():
            assert raw_query not in key
            assert "mutation" not in key
            assert len(key) == 64  # Hexadecimal SHA-256 length

    def test_ttl_expiration(self) -> None:
        """Verify entries expire and return None after TTL."""
        cache = QueryEmbeddingCache(max_size=10, ttl_seconds=0.05)  # 50ms TTL
        vec = [0.4] * 768

        cache.set("fast expiration query", vec)
        assert cache.get("fast expiration query") == vec

        time.sleep(0.06)
        assert cache.get("fast expiration query") is None
        assert cache.stats()["size"] == 0

    def test_lru_eviction(self) -> None:
        """Verify least recently used entry is evicted when capacity is reached."""
        cache = QueryEmbeddingCache(max_size=3, ttl_seconds=60.0)
        v1 = [0.1] * 768
        v2 = [0.2] * 768
        v3 = [0.3] * 768
        v4 = [0.4] * 768

        cache.set("query 1", v1)
        cache.set("query 2", v2)
        cache.set("query 3", v3)
        assert cache.stats()["size"] == 3

        # Access query 1 so query 2 becomes LRU
        cache.get("query 1")

        # Insert 4th query -> query 2 should be evicted
        cache.set("query 4", v4)
        assert cache.stats()["size"] == 3
        assert cache.stats()["evictions"] == 1
        assert cache.get("query 2") is None
        assert cache.get("query 1") == v1
        assert cache.get("query 3") == v3
        assert cache.get("query 4") == v4

    def test_invalidation_and_clear(self) -> None:
        """Verify invalidation removes targeted item and clear empties cache."""
        cache = QueryEmbeddingCache(max_size=10, ttl_seconds=60.0)
        cache.set("query a", [0.1] * 768)
        cache.set("query b", [0.2] * 768)

        assert cache.invalidate("query a") is True
        assert cache.get("query a") is None
        assert cache.get("query b") is not None

        cache.clear()
        assert cache.stats()["size"] == 0
        assert cache.get("query b") is None


# ==============================================================================
# 2. EmbeddingService Cache Integration Tests
# ==============================================================================


class TestEmbeddingServiceCacheIntegration:
    """Test suite verifying EmbeddingService utilizes QueryEmbeddingCache."""

    def test_embedding_service_caches_single_query(self) -> None:
        """Verify single query embedding is cached and subsequent call avoids client embed."""
        mock_client = MagicMock()
        mock_client.embed = AsyncMock(return_value=[[0.5] * 768])
        cache = QueryEmbeddingCache(max_size=10, ttl_seconds=60.0)

        svc = EmbeddingService(llm_client=mock_client, cache=cache)

        # First call: cache miss, calls client.embed
        emb1 = asyncio.run(svc.get_embedding("What is lung cancer?"))
        assert len(emb1) == 768
        assert mock_client.embed.await_count == 1

        # Second call: cache hit, client.embed NOT called
        emb2 = asyncio.run(svc.get_embedding("What is lung cancer?"))
        assert emb2 == emb1
        assert mock_client.embed.await_count == 1  # Still 1!


# ==============================================================================
# 3. Safety Short-Circuit Tests (Phase 5.3)
# ==============================================================================


class TestSafetyEarlyShortCircuit:
    """Test suite verifying zero retrieval and zero embeddings on direct safety refusals."""

    def test_direct_diagnosis_query_short_circuits_retriever(self) -> None:
        """Verify 'Do I have cancer?' bypasses embedding and DB retrieval in RAGRetriever."""
        mock_emb_svc = MagicMock()
        mock_emb_svc.get_embedding = AsyncMock(return_value=[0.1] * 768)
        mock_session = AsyncMock()

        safety = SafetyEvaluator()
        retriever = RAGRetriever(
            session=mock_session,
            embedding_service=mock_emb_svc,
            safety_evaluator=safety,
        )

        telemetry = RAGTelemetryContext(query="Do I have cancer?")
        context = asyncio.run(
            retriever.retrieve_context(
                query="Do I have cancer?",
                telemetry=telemetry,
            )
        )

        # Embedding service and DB session must NOT have been called
        assert mock_emb_svc.get_embedding.await_count == 0
        assert mock_session.execute.await_count == 0
        assert len(context.chunks) == 0
        assert "safety_refusal" in context.reason

    def test_direct_treatment_prescription_short_circuits_retriever(self) -> None:
        """Verify chemotherapy prescription query bypasses embedding and DB retrieval."""
        mock_emb_svc = MagicMock()
        mock_emb_svc.get_embedding = AsyncMock(return_value=[0.1] * 768)
        mock_session = AsyncMock()

        safety = SafetyEvaluator()
        retriever = RAGRetriever(
            session=mock_session,
            embedding_service=mock_emb_svc,
            safety_evaluator=safety,
        )

        context = asyncio.run(
            retriever.retrieve_context("What chemotherapy should I personally take?")
        )

        assert mock_emb_svc.get_embedding.await_count == 0
        assert mock_session.execute.await_count == 0
        assert len(context.chunks) == 0
        assert "safety_refusal" in context.reason

    def test_staging_boundary_query_does_not_short_circuit(self) -> None:
        """Verify educational staging query executes retrieval to provide safety context."""
        mock_emb_svc = MagicMock()
        mock_emb_svc.get_embedding = AsyncMock(return_value=[0.1] * 768)
        mock_session = AsyncMock()
        mock_session.scalar.return_value = uuid.uuid4()
        mock_exec = MagicMock()
        mock_exec.all.return_value = []
        mock_session.execute.return_value = mock_exec

        safety = SafetyEvaluator()
        retriever = RAGRetriever(
            session=mock_session,
            embedding_service=mock_emb_svc,
            safety_evaluator=safety,
        )

        # Staging queries have educational guidance, NOT deterministic refusal
        context = asyncio.run(
            retriever.retrieve_context("Can this image tell me my cancer stage?")
        )

        # Must execute embedding and retrieval for educational guidance
        assert mock_emb_svc.get_embedding.await_count == 1
        assert mock_session.execute.await_count >= 1


# ==============================================================================
# 4. Database Projection & One-Time Record Check Tests
# ==============================================================================


class TestDatabaseProjectionAndRecordCheck:
    """Test suite verifying load_only projection and record caching in RAGRetriever."""

    def test_has_records_verified_only_once(self) -> None:
        """Verify scalar check for knowledge records executes at most once per retriever."""
        mock_emb_svc = MagicMock()
        mock_emb_svc.get_embedding = AsyncMock(return_value=[0.1] * 768)
        mock_session = AsyncMock()
        mock_session.scalar.return_value = uuid.uuid4()
        mock_exec = MagicMock()
        mock_exec.all.return_value = []
        mock_session.execute.return_value = mock_exec

        retriever = RAGRetriever(
            session=mock_session,
            embedding_service=mock_emb_svc,
        )

        # Call 1
        asyncio.run(retriever.retrieve_context("What is lung cancer?"))
        assert mock_session.scalar.await_count == 1

        # Call 2
        asyncio.run(retriever.retrieve_context("What is colon cancer?"))
        # Must still be 1 (record check was cached)
        assert mock_session.scalar.await_count == 1


# ==============================================================================
# 5. Gemini Client Error Classification Tests
# ==============================================================================


class TestGeminiClientErrorClassification:
    """Test suite verifying error classification into retryable vs non-retryable."""

    def test_non_retryable_errors(self) -> None:
        """Verify deterministic client-side errors and safety blocks are non-retryable."""
        assert is_retryable_llm_error(RuntimeError("400 Bad Request: Invalid argument")) is False
        assert is_retryable_llm_error(RuntimeError("401 Unauthenticated API key")) is False
        assert is_retryable_llm_error(RuntimeError("403 Permission denied")) is False
        assert is_retryable_llm_error(RuntimeError("Content blocked by SAFETY filter")) is False
        assert is_retryable_llm_error(RuntimeError("Content filter violation: HARM_CATEGORY")) is False

    def test_retryable_errors(self) -> None:
        """Verify transient network, rate limits, and server errors are retryable."""
        assert is_retryable_llm_error(asyncio.TimeoutError()) is True
        assert is_retryable_llm_error(RuntimeError("429 Resource has been exhausted (quota)")) is True
        assert is_retryable_llm_error(RuntimeError("500 Internal server error")) is True
        assert is_retryable_llm_error(RuntimeError("503 Service Unavailable")) is True
        assert is_retryable_llm_error(RuntimeError("504 Gateway Timeout: deadline_exceeded")) is True
        assert is_retryable_llm_error(RuntimeError("Connection reset by peer")) is True
