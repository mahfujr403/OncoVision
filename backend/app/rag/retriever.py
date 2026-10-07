"""Two-stage, provenance-preserving medical RAG retriever (Phase 3).

Features:
- Query intent and scope classification (QueryScopeClassifier)
- SQL metadata pre-filtering (domain & class scope isolation)
- pgvector HNSW cosine distance search (<=>)
- Explainable two-stage relevance re-ranking
- Source diversity optimization across authoritative literature (NCI, CAP, NCBI, PMC)
- Citation-ready context formatting preserving clickable URLs and tiers
- Full backward-compatibility with existing chat_service and test callers
"""

from __future__ import annotations

import logging
import time
from typing import Any, List

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.core.settings import get_settings
from app.models.knowledge_embedding import KnowledgeEmbedding
from app.rag.classifier import (
    ClassScope,
    QueryDomain,
    QueryIntent,
    QueryScope,
    QueryScopeClassifier,
)
from app.rag.safety import SafetyEvaluator
from app.rag.embeddings import EmbeddingService
from app.rag.observability import (
    EVENT_RETRIEVAL_COMPLETED,
    EVENT_RETRIEVAL_EMPTY,
    RAGErrorCategory,
    RAGTelemetryContext,
    log_rag_event,
)

logger = logging.getLogger(__name__)


class RetrievedDocument(BaseModel):
    """Enriched document chunk preserving complete provenance and citation metadata."""

    content: str
    source: str
    topic: str
    similarity: float

    # Phase 3 provenance and citation fields
    document_id: str | None = None
    document_title: str | None = None
    domain: str | None = None
    class_scope: str | list[str] | None = None
    source_title: str | None = None
    source_url: str | None = None
    source_tier: int | None = None
    citation: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# Type alias for clear architectural semantics
RetrievedChunk = RetrievedDocument


class RetrievedContext(BaseModel):
    """Structured context output containing chunks, query scope, and citation formatted text."""

    chunks: list[RetrievedDocument] = Field(default_factory=list)
    query_scope: QueryScope
    reason: str = "success"
    formatted_context: str = ""
    retrieval_latency_ms: float = 0.0
    classification_latency_ms: float = 0.0



class RAGRetriever:
    """Production retrieval service for OncoVision medical RAG subsystem."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService,
        classifier: QueryScopeClassifier | None = None,
        safety_evaluator: SafetyEvaluator | None = None,
    ) -> None:
        self.session = session
        self.embedding_service = embedding_service
        self.classifier = classifier or QueryScopeClassifier()
        self.safety_evaluator = safety_evaluator
        self.settings = get_settings()
        self._has_records_verified: bool = False

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ) -> List[RetrievedDocument]:
        """Retrieve relevant medical documents (backward-compatible method)."""
        ctx = await self.retrieve_context(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )
        return ctx.chunks

    async def retrieve_context(
        self,
        query: str,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        candidate_pool_size: int | None = None,
        telemetry: RAGTelemetryContext | None = None,
    ) -> RetrievedContext:
        """Execute complete two-stage, domain-filtered, and source-diverse retrieval."""
        effective_top_k = top_k or self.settings.RAG_TOP_K
        effective_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else self.settings.RAG_SIMILARITY_THRESHOLD
        )
        effective_pool_size = (
            candidate_pool_size or self.settings.RAG_CANDIDATE_POOL_SIZE
        )

        r_start = time.perf_counter()

        # 1. Query Scope and Intent Classification
        c_start = time.perf_counter()
        query_scope = self.classifier.classify(query)
        classification_ms = round((time.perf_counter() - c_start) * 1000, 2)

        if not query or not query.strip():
            retrieval_ms = round((time.perf_counter() - r_start) * 1000, 2)
            if telemetry:
                telemetry.classification_ms = classification_ms
                telemetry.retrieval_ms = retrieval_ms
                telemetry.record_event(
                    EVENT_RETRIEVAL_EMPTY,
                    reason="empty_query",
                    retrieval_ms=retrieval_ms,
                )
            return RetrievedContext(
                chunks=[],
                query_scope=query_scope,
                reason="empty_query",
                formatted_context="No relevant context found.",
                retrieval_latency_ms=retrieval_ms,
                classification_latency_ms=classification_ms,
            )

        # Early Safety Refusal Short-Circuit (Phase 5.3):
        # Bypasses query embedding API call and database retrieval when a query
        # deterministically violates medical safety boundaries (diagnosis/prescription)
        if self.safety_evaluator:
            safety_eval = self.safety_evaluator.evaluate_query(query)
            if safety_eval.requires_deterministic_refusal:
                retrieval_ms = round((time.perf_counter() - r_start) * 1000, 2)
                refusal_reason = safety_eval.boundary.value if safety_eval.boundary else "safety_refusal"
                if telemetry:
                    telemetry.classification_ms = classification_ms
                    telemetry.retrieval_ms = retrieval_ms
                    telemetry.record_event(
                        EVENT_RETRIEVAL_EMPTY,
                        reason=f"safety_refusal:{refusal_reason}",
                        retrieval_ms=retrieval_ms,
                    )
                return RetrievedContext(
                    chunks=[],
                    query_scope=query_scope,
                    reason=f"safety_refusal:{refusal_reason}",
                    formatted_context="Request refused by clinical safety boundary.",
                    retrieval_latency_ms=retrieval_ms,
                    classification_latency_ms=classification_ms,
                )

        try:
            # Check if database has any records (verified once per retriever instance to minimize query overhead)
            if not self._has_records_verified:
                has_records = await self.session.scalar(select(KnowledgeEmbedding.id).limit(1))
                if has_records is None:
                    retrieval_ms = round((time.perf_counter() - r_start) * 1000, 2)
                    if telemetry:
                        telemetry.classification_ms = classification_ms
                        telemetry.retrieval_ms = retrieval_ms
                        telemetry.record_event(
                            EVENT_RETRIEVAL_EMPTY,
                            reason="empty_knowledge_base",
                            retrieval_ms=retrieval_ms,
                        )
                    return RetrievedContext(
                        chunks=[],
                        query_scope=query_scope,
                        reason="empty_knowledge_base",
                        formatted_context="No relevant context found.",
                        retrieval_latency_ms=retrieval_ms,
                        classification_latency_ms=classification_ms,
                    )
                self._has_records_verified = True

            # Generate query embedding using gemini-embedding-2 (768 dimensions)
            try:
                query_embedding = await self.embedding_service.get_embedding(query)
            except Exception as emb_err:
                retrieval_ms = round((time.perf_counter() - r_start) * 1000, 2)
                logger.warning("Embedding generation failed: %s", emb_err)
                if telemetry:
                    telemetry.classification_ms = classification_ms
                    telemetry.retrieval_ms = retrieval_ms
                    telemetry.error_category = RAGErrorCategory.EMBEDDING_ERROR.value
                    telemetry.record_event(
                        EVENT_RETRIEVAL_EMPTY,
                        reason="embedding_generation_failed",
                        error_category=RAGErrorCategory.EMBEDDING_ERROR.value,
                        retrieval_ms=retrieval_ms,
                    )
                return RetrievedContext(
                    chunks=[],
                    query_scope=query_scope,
                    reason="embedding_generation_failed",
                    formatted_context="No relevant context found.",
                    retrieval_latency_ms=retrieval_ms,
                    classification_latency_ms=classification_ms,
                )

            if not query_embedding or len(query_embedding) != 768:
                retrieval_ms = round((time.perf_counter() - r_start) * 1000, 2)
                logger.warning("Invalid or empty embedding for query length %d", len(query))
                if telemetry:
                    telemetry.classification_ms = classification_ms
                    telemetry.retrieval_ms = retrieval_ms
                    telemetry.error_category = RAGErrorCategory.EMBEDDING_ERROR.value
                    telemetry.record_event(
                        EVENT_RETRIEVAL_EMPTY,
                        reason="embedding_generation_failed",
                        error_category=RAGErrorCategory.EMBEDDING_ERROR.value,
                        retrieval_ms=retrieval_ms,
                    )
                return RetrievedContext(
                    chunks=[],
                    query_scope=query_scope,
                    reason="embedding_generation_failed",
                    formatted_context="No relevant context found.",
                    retrieval_latency_ms=retrieval_ms,
                    classification_latency_ms=classification_ms,
                )

            # 2. Stage 1: Vector Search + SQL Metadata Filtering
            candidates = await self._retrieve_candidates(
                query_embedding=query_embedding,
                query_scope=query_scope,
                threshold=effective_threshold,
                pool_size=effective_pool_size,
            )

            if not candidates:
                # Fallback to broader retrieval if domain filtering was overly restrictive
                if query_scope.domain is not None:
                    candidates = await self._retrieve_candidates(
                        query_embedding=query_embedding,
                        query_scope=QueryScope(
                            domain=None,
                            class_scopes=[],
                            intent=query_scope.intent,
                            confidence=0.5,
                            requires_safety_context=query_scope.requires_safety_context,
                        ),
                        threshold=effective_threshold,
                        pool_size=effective_pool_size,
                    )

            if not candidates:
                retrieval_ms = round((time.perf_counter() - r_start) * 1000, 2)
                if telemetry:
                    telemetry.classification_ms = classification_ms
                    telemetry.retrieval_ms = retrieval_ms
                    telemetry.domain = query_scope.domain.value if query_scope.domain else None
                    telemetry.intent = query_scope.intent.value
                    telemetry.record_event(
                        EVENT_RETRIEVAL_EMPTY,
                        reason="no_relevant_knowledge_found",
                        retrieval_ms=retrieval_ms,
                    )
                return RetrievedContext(
                    chunks=[],
                    query_scope=query_scope,
                    reason="no_relevant_knowledge_found",
                    formatted_context="No relevant context found.",
                    retrieval_latency_ms=retrieval_ms,
                    classification_latency_ms=classification_ms,
                )

            # 3. Stage 2: Explainable Re-ranking & Source Diversity Optimization
            ranked_chunks = self._rerank_and_diversify(
                candidates=candidates,
                query_scope=query_scope,
                top_k=effective_top_k,
            )

            formatted = self.format_context(ranked_chunks)
            retrieval_ms = round((time.perf_counter() - r_start) * 1000, 2)

            sims = [c.similarity for c in ranked_chunks if c.similarity is not None]
            top_sim = max(sims) if sims else 0.0
            mean_sim = round(sum(sims) / len(sims), 4) if sims else 0.0
            domain_val = query_scope.domain.value if query_scope.domain else None

            if telemetry:
                telemetry.classification_ms = classification_ms
                telemetry.retrieval_ms = retrieval_ms
                telemetry.domain = domain_val
                telemetry.intent = query_scope.intent.value
                telemetry.retrieved_chunks = len(ranked_chunks)
                telemetry.top_similarity = top_sim
                telemetry.mean_similarity = mean_sim
                telemetry.record_event(
                    EVENT_RETRIEVAL_COMPLETED,
                    retrieved_chunks=len(ranked_chunks),
                    top_similarity=top_sim,
                    mean_similarity=mean_sim,
                    domain=domain_val,
                    retrieval_ms=retrieval_ms,
                )

            return RetrievedContext(
                chunks=ranked_chunks,
                query_scope=query_scope,
                reason="success",
                formatted_context=formatted,
                retrieval_latency_ms=retrieval_ms,
                classification_latency_ms=classification_ms,
            )

        except Exception as e:
            retrieval_ms = round((time.perf_counter() - r_start) * 1000, 2)
            logger.warning("RAG retrieval failed gracefully: %s", e, exc_info=True)
            try:
                await self.session.rollback()
            except Exception:
                pass
            if telemetry:
                telemetry.classification_ms = classification_ms
                telemetry.retrieval_ms = retrieval_ms
                telemetry.error_category = RAGErrorCategory.RETRIEVAL_ERROR.value
                telemetry.record_event(
                    EVENT_RETRIEVAL_EMPTY,
                    reason="retrieval_error",
                    error_category=RAGErrorCategory.RETRIEVAL_ERROR.value,
                    retrieval_ms=retrieval_ms,
                )
            return RetrievedContext(
                chunks=[],
                query_scope=query_scope,
                reason=f"retrieval_error: {str(e)}",
                formatted_context="No relevant context found.",
                retrieval_latency_ms=retrieval_ms,
                classification_latency_ms=classification_ms,
            )


    async def _retrieve_candidates(
        self,
        query_embedding: list[float],
        query_scope: QueryScope,
        threshold: float,
        pool_size: int,
    ) -> list[tuple[KnowledgeEmbedding, float]]:
        """Query pgvector HNSW index with domain & policy constraints."""
        distance_expr = KnowledgeEmbedding.embedding.cosine_distance(query_embedding)
        similarity_expr = (1.0 - distance_expr).label("similarity")

        # Base filters: Always isolate non-clinical developer/platform info
        filters = [
            KnowledgeEmbedding.topic.notin_(["developer_info", "platform_info"]),
            similarity_expr >= threshold,
        ]

        # Safety policy isolation: Only retrieve safety policy when specifically needed
        if not query_scope.requires_safety_context and query_scope.domain != QueryDomain.SAFETY_POLICY:
            filters.append(
                (KnowledgeEmbedding.domain != QueryDomain.SAFETY_POLICY.value)
                | (KnowledgeEmbedding.domain.is_(None))
            )

        # Domain-specific SQL filtering to prevent cross-contamination
        if query_scope.domain == QueryDomain.COLON:
            filters.append(
                KnowledgeEmbedding.domain.in_([
                    QueryDomain.COLON.value,
                    QueryDomain.HISTOPATHOLOGY.value,
                    QueryDomain.GENERAL_ONCOLOGY.value,
                    QueryDomain.CLASSIFIER_CONTEXT.value,
                    QueryDomain.CLINICAL_EXPLANATION.value,
                ])
            )
        elif query_scope.domain == QueryDomain.LUNG:
            filters.append(
                KnowledgeEmbedding.domain.in_([
                    QueryDomain.LUNG.value,
                    QueryDomain.HISTOPATHOLOGY.value,
                    QueryDomain.GENERAL_ONCOLOGY.value,
                    QueryDomain.CLASSIFIER_CONTEXT.value,
                    QueryDomain.CLINICAL_EXPLANATION.value,
                ])
            )
        elif query_scope.domain == QueryDomain.COMPARISON:
            filters.append(
                KnowledgeEmbedding.domain.in_([
                    QueryDomain.COMPARISON.value,
                    QueryDomain.CLASSIFIER_CONTEXT.value,
                    QueryDomain.COLON.value,
                    QueryDomain.LUNG.value,
                    QueryDomain.HISTOPATHOLOGY.value,
                ])
            )
        elif query_scope.domain == QueryDomain.SAFETY_POLICY:
            filters.append(
                KnowledgeEmbedding.domain.in_([
                    QueryDomain.SAFETY_POLICY.value,
                    QueryDomain.GENERAL_ONCOLOGY.value,
                ])
            )

        stmt = (
            select(KnowledgeEmbedding, similarity_expr)
            .options(
                load_only(
                    KnowledgeEmbedding.id,
                    KnowledgeEmbedding.document_id,
                    KnowledgeEmbedding.document_title,
                    KnowledgeEmbedding.domain,
                    KnowledgeEmbedding.topic,
                    KnowledgeEmbedding.source,
                    KnowledgeEmbedding.content,
                    KnowledgeEmbedding.chunk_metadata,
                )
            )
            .where(*filters)
            .order_by(distance_expr)
            .limit(pool_size)
        )

        result = await self.session.execute(stmt)
        return [(row[0], float(row[1])) for row in result.all()]

    def _rerank_and_diversify(
        self,
        candidates: list[tuple[KnowledgeEmbedding, float]],
        query_scope: QueryScope,
        top_k: int,
    ) -> list[RetrievedDocument]:
        """Score candidate chunks with explainable bonuses and enforce source diversity."""
        scored_candidates: list[tuple[KnowledgeEmbedding, float]] = []

        target_classes = {cs.value for cs in query_scope.class_scopes}

        for record, base_similarity in candidates:
            score = base_similarity
            meta = record.chunk_metadata or {}

            # 1. Domain alignment boost
            if query_scope.domain and record.domain == query_scope.domain.value:
                score += 0.06

            # 2. Class scope alignment boost
            chunk_class = meta.get("class_scope")
            if chunk_class:
                if isinstance(chunk_class, list) and any(c in target_classes for c in chunk_class):
                    score += 0.06
                elif isinstance(chunk_class, str) and chunk_class in target_classes:
                    score += 0.06

            # 3. Intent alignment boost
            content_lower = record.content.lower()
            if query_scope.intent == QueryIntent.IMMUNOHISTOCHEMISTRY and any(
                kw in content_lower for kw in ["ihc", "p40", "ttf-1", "ck7", "ck20", "napsin"]
            ):
                score += 0.04
            elif query_scope.intent == QueryIntent.BIOMARKER and any(
                kw in content_lower for kw in ["egfr", "kras", "alk", "braf", "mutation", "biomarker"]
            ):
                score += 0.04
            elif query_scope.intent == QueryIntent.STAGING and any(
                kw in content_lower for kw in ["tnm", "stage", "staging", "t1", "t2", "t3", "t4"]
            ):
                score += 0.04
            elif query_scope.intent == QueryIntent.HISTOPATHOLOGY and any(
                kw in content_lower for kw in ["histolog", "morphology", "crypts", "lepidic", "cribriform", "budding"]
            ):
                score += 0.03

            # 4. Safety policy bonus when safety context is requested
            if query_scope.requires_safety_context and record.domain == QueryDomain.SAFETY_POLICY.value:
                score += 0.08

            scored_candidates.append((record, score))

        # Sort candidates by combined score descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Source diversity check: limit chunks per document during primary pass
        selected_candidates: list[tuple[KnowledgeEmbedding, float]] = []
        doc_counts: dict[str, int] = {}
        max_chunks_per_doc = 2

        # Primary pass with document diversity constraint
        for record, score in scored_candidates:
            doc_id = record.document_id or record.source
            if doc_counts.get(doc_id, 0) < max_chunks_per_doc:
                selected_candidates.append((record, score))
                doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
                if len(selected_candidates) >= top_k:
                    break

        # Fallback pass: fill remaining slots from candidates if diversity limited total count
        if len(selected_candidates) < top_k:
            selected_ids = {r.id for r, _ in selected_candidates}
            for record, score in scored_candidates:
                if record.id not in selected_ids:
                    selected_candidates.append((record, score))
                    if len(selected_candidates) >= top_k:
                        break

        # Convert to RetrievedDocument models with complete provenance
        documents: list[RetrievedDocument] = []
        for record, score in selected_candidates:
            meta = record.chunk_metadata or {}
            documents.append(
                RetrievedDocument(
                    content=record.content,
                    source=record.source,
                    topic=record.topic,
                    similarity=round(score, 4),
                    document_id=record.document_id,
                    document_title=record.document_title,
                    domain=record.domain,
                    class_scope=meta.get("class_scope"),
                    source_title=meta.get("source_title"),
                    source_url=meta.get("source_url"),
                    source_tier=meta.get("source_tier"),
                    citation=meta.get("citation"),
                    metadata=meta,
                )
            )

        return documents

    def format_context(self, documents: List[RetrievedDocument]) -> str:
        """Format retrieved documents into structured citation-ready context for LLM."""
        if not documents:
            return "No relevant context found."

        blocks = []
        for i, doc in enumerate(documents, 1):
            title = doc.source_title or doc.topic or "Clinical Knowledge Source"
            url = doc.source_url or "https://www.cancer.gov"
            tier = doc.source_tier if doc.source_tier is not None else 2
            doc_name = doc.document_title or doc.source or "Clinical Reference"

            block = (
                f"[Source {i}]\n"
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Tier: {tier}\n"
                f"Document: {doc_name}\n"
                f"Content:\n"
                f"{doc.content.strip()}"
            )
            blocks.append(block)

        return "\n\n".join(blocks)
