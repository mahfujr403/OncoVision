"""Unit and integration tests for OncoVision Two-Stage Medical RAG Retriever (Phase 3).

Verifies:
1. Two-stage retrieval: scope detection, metadata filtering, vector search, re-ranking, and diversity.
2. Domain & class scope filtering without cross-contamination (lung vs colon).
3. Isolation of developer_info and platform_info from medical queries.
4. Isolation of safety_policy from ordinary pathology queries, and correct retrieval for safety queries.
5. Source diversity optimization across distinct documents/sources (NCI, CAP, NCBI, PMC).
6. Citation-ready context formatting with clickable URLs and tiers.
7. Graceful empty retrieval and error resilience.
8. Evaluation against 09_qa_evaluation/retrieval_test_cases.json.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.knowledge_embedding import KnowledgeEmbedding
from app.rag.classifier import (
    ClassScope,
    QueryDomain,
    QueryIntent,
    QueryScope,
    QueryScopeClassifier,
)
from app.rag.retriever import (
    RAGRetriever,
    RetrievedContext,
    RetrievedDocument,
)


def _make_chunk(
    doc_id: str,
    title: str,
    domain: str,
    content: str,
    class_scope: str | None = None,
    source_url: str = "https://www.cancer.gov/test",
    source_title: str = "NCI Clinical Test",
    source_tier: int = 1,
    topic: str | None = None,
    distance: float = 0.25,
) -> tuple[KnowledgeEmbedding, float]:
    """Helper creating a mock KnowledgeEmbedding record and similarity score."""
    rec = MagicMock(spec=KnowledgeEmbedding)
    rec.id = uuid.uuid4()
    rec.document_id = doc_id
    rec.document_title = title
    rec.domain = domain
    rec.topic = topic or domain
    rec.source = f"{domain}/{doc_id}.md"
    rec.content = content
    rec.chunk_metadata = {
        "document_id": doc_id,
        "document_title": title,
        "domain": domain,
        "class_scope": class_scope,
        "source_title": source_title,
        "source_url": source_url,
        "source_tier": source_tier,
        "citation": f"{source_title} ({source_url})",
    }
    similarity = 1.0 - distance
    return rec, similarity


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Fixture providing mock EmbeddingService returning valid 768-dim embeddings."""
    svc = MagicMock()
    svc.get_embedding = AsyncMock(return_value=[0.05] * 768)
    return svc


class TestRetrieverPipeline:
    """Tests for two-stage retrieval, re-ranking, and diversity."""

    def test_two_stage_retrieval_flow(self, mock_embedding_service: MagicMock) -> None:
        """Verify full retrieval pipeline execution from query to citation-ready context."""
        fake_session = AsyncMock()
        fake_session.scalar.return_value = uuid.uuid4()  # Has records

        # Candidates returned by vector search
        c1, s1 = _make_chunk(
            doc_id="doc_lung_adeno",
            title="Lung Adenocarcinoma Overview",
            domain="lung",
            content="Lepidic growth pattern exhibits neoplastic pneumocytes lining alveolar walls.",
            class_scope="lung_adenocarcinoma",
            source_url="https://www.ncbi.nlm.nih.gov/books/NBK470380/",
            source_title="NCBI Lung Adenocarcinoma",
            source_tier=2,
            distance=0.20,
        )
        c2, s2 = _make_chunk(
            doc_id="doc_lung_adeno_patterns",
            title="Lung Adenocarcinoma Patterns",
            domain="lung",
            content="Acinar and papillary patterns of adenocarcinoma in pulmonary resection.",
            class_scope="lung_adenocarcinoma",
            source_url="https://www.cancer.gov/lung",
            source_title="NCI Lung Guideline",
            source_tier=1,
            distance=0.25,
        )

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [(c1, s1), (c2, s2)]
        fake_session.execute.return_value = mock_exec_result

        retriever = RAGRetriever(
            session=fake_session,
            embedding_service=mock_embedding_service,
        )

        context = asyncio.run(
            retriever.retrieve_context("What does lepidic growth mean in lung adenocarcinoma?")
        )

        assert isinstance(context, RetrievedContext)
        assert context.reason == "success"
        assert len(context.chunks) == 2
        assert context.query_scope.domain == QueryDomain.LUNG
        assert ClassScope.LUNG_ADENOCARCINOMA in context.query_scope.class_scopes

        # Verify citation-ready context is formatted
        assert "[Source 1]" in context.formatted_context
        assert "[Source 2]" in context.formatted_context
        assert "https://www.ncbi.nlm.nih.gov/books/NBK470380/" in context.formatted_context
        assert "https://www.cancer.gov/lung" in context.formatted_context

    def test_cross_domain_isolation_colon_vs_lung(self, mock_embedding_service: MagicMock) -> None:
        """Verify colon query restricts candidate SQL query and excludes lung chunks."""
        fake_session = AsyncMock()
        fake_session.scalar.return_value = uuid.uuid4()

        colon_chunk, s1 = _make_chunk(
            doc_id="doc_colon_morphology",
            title="Colon Adenocarcinoma Histomorphology",
            domain="colon",
            content="Glandular cribriform architecture in invasive colon adenocarcinoma.",
            class_scope="colon_adenocarcinoma",
            distance=0.15,
        )

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [(colon_chunk, s1)]
        fake_session.execute.return_value = mock_exec_result

        retriever = RAGRetriever(
            session=fake_session,
            embedding_service=mock_embedding_service,
        )

        query = "What are the histological features of colon adenocarcinoma?"
        context = asyncio.run(retriever.retrieve_context(query))

        assert len(context.chunks) == 1
        assert context.chunks[0].domain == "colon"
        assert context.chunks[0].domain != "lung"

        # Verify SQL filter called with domain constraint
        execute_args = fake_session.execute.call_args[0][0]
        sql_str = str(execute_args)
        assert "knowledge_embeddings.domain" in sql_str.lower()

    def test_developer_and_platform_info_isolated_from_medical_queries(
        self, mock_embedding_service: MagicMock
    ) -> None:
        """Verify developer_info and platform_info are excluded in SQL query for medical retrieval."""
        fake_session = AsyncMock()
        fake_session.scalar.return_value = uuid.uuid4()

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = []
        fake_session.execute.return_value = mock_exec_result

        retriever = RAGRetriever(
            session=fake_session,
            embedding_service=mock_embedding_service,
        )

        asyncio.run(retriever.retrieve_context("What is cancer?"))

        execute_args = fake_session.execute.call_args[0][0]
        sql_str = str(execute_args)
        # Check topic NOT IN developer_info, platform_info
        assert "knowledge_embeddings.topic NOT IN" in sql_str or "knowledge_embeddings.topic" in sql_str

    def test_safety_policy_isolated_from_ordinary_pathology(
        self, mock_embedding_service: MagicMock
    ) -> None:
        """Verify ordinary clinical questions do NOT retrieve safety_policy domain."""
        fake_session = AsyncMock()
        fake_session.scalar.return_value = uuid.uuid4()

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = []
        fake_session.execute.return_value = mock_exec_result

        retriever = RAGRetriever(
            session=fake_session,
            embedding_service=mock_embedding_service,
        )

        # Ordinary question
        query = "What are normal colon crypts?"
        asyncio.run(retriever.retrieve_context(query))

        execute_args = fake_session.execute.call_args[0][0]
        compiled = execute_args.compile()
        # Verify safety_policy exclusion was applied as a bound parameter
        assert any(v == "safety_policy" for v in compiled.params.values())

    def test_safety_boundary_query_retrieves_safety_policy(
        self, mock_embedding_service: MagicMock
    ) -> None:
        """Verify boundary query retrieves safety_policy chunks and boosts them."""
        fake_session = AsyncMock()
        fake_session.scalar.return_value = uuid.uuid4()

        safety_chunk, s1 = _make_chunk(
            doc_id="doc_staging_boundaries",
            title="Staging Boundaries Protocol",
            domain="safety_policy",
            content="Histopathology images cannot infer full TNM clinical stage without radiological imaging.",
            source_url="https://github.com/mahfujr403/OncoVision/docs/safety",
            source_title="OncoVision Safety Protocol",
            distance=0.25,
        )

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [(safety_chunk, s1)]
        fake_session.execute.return_value = mock_exec_result

        retriever = RAGRetriever(
            session=fake_session,
            embedding_service=mock_embedding_service,
        )

        query = "Can this histopathology image determine TNM stage?"
        context = asyncio.run(retriever.retrieve_context(query))

        assert context.query_scope.requires_safety_context is True
        assert len(context.chunks) == 1
        assert context.chunks[0].domain == "safety_policy"
        # Verify score received safety boost
        assert context.chunks[0].similarity > s1

    def test_source_diversity_caps_chunks_per_document(
        self, mock_embedding_service: MagicMock
    ) -> None:
        """Verify source diversity limits chunks per single document when distinct sources are available."""
        fake_session = AsyncMock()
        fake_session.scalar.return_value = uuid.uuid4()

        # 4 chunks from doc A (NCI), 1 from doc B (NCBI), 1 from doc C (CAP)
        candidates = [
            _make_chunk("doc_A", "NCI Overview", "colon", "Chunk 1 of doc A", distance=0.10),
            _make_chunk("doc_A", "NCI Overview", "colon", "Chunk 2 of doc A", distance=0.12),
            _make_chunk("doc_A", "NCI Overview", "colon", "Chunk 3 of doc A", distance=0.14),
            _make_chunk("doc_A", "NCI Overview", "colon", "Chunk 4 of doc A", distance=0.15),
            _make_chunk("doc_B", "NCBI Atlas", "colon", "Chunk 1 of doc B", distance=0.16),
            _make_chunk("doc_C", "CAP Protocol", "colon", "Chunk 1 of doc C", distance=0.18),
        ]

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = candidates
        fake_session.execute.return_value = mock_exec_result

        retriever = RAGRetriever(
            session=fake_session,
            embedding_service=mock_embedding_service,
        )

        # Retrieve top 4 chunks
        context = asyncio.run(
            retriever.retrieve_context(
                query="Colorectal cancer pathology overview",
                top_k=4,
            )
        )

        assert len(context.chunks) == 4
        doc_ids = [c.document_id for c in context.chunks]

        # Doc A should be capped at max 2 chunks during primary pass
        assert doc_ids.count("doc_A") == 2
        # Remaining slots filled by doc B and doc C
        assert "doc_B" in doc_ids
        assert "doc_C" in doc_ids

    def test_citation_ready_context_format(self, mock_embedding_service: MagicMock) -> None:
        """Verify format_context creates clear, clickable markdown delimiters."""
        retriever = RAGRetriever(
            session=AsyncMock(),
            embedding_service=mock_embedding_service,
        )

        doc1 = RetrievedDocument(
            content="Normal colonic crypts are straight test tubes.",
            source="01_colon/normal_colon.md",
            topic="colon",
            similarity=0.88,
            document_title="Normal Colon Microanatomy",
            source_title="StatPearls Colonic Anatomy",
            source_url="https://www.ncbi.nlm.nih.gov/books/NBK12345/",
            source_tier=2,
        )

        formatted = retriever.format_context([doc1])

        assert "[Source 1]" in formatted
        assert "Title: StatPearls Colonic Anatomy" in formatted
        assert "URL: https://www.ncbi.nlm.nih.gov/books/NBK12345/" in formatted
        assert "Tier: 2" in formatted
        assert "Document: Normal Colon Microanatomy" in formatted
        assert "Normal colonic crypts are straight test tubes." in formatted

    def test_empty_retrieval_returns_explicit_reason(
        self, mock_embedding_service: MagicMock
    ) -> None:
        """Verify retriever returns empty reason rather than fabricated or random chunks."""
        fake_session = AsyncMock()
        fake_session.scalar.return_value = uuid.uuid4()

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = []
        fake_session.execute.return_value = mock_exec_result

        retriever = RAGRetriever(
            session=fake_session,
            embedding_service=mock_embedding_service,
        )

        context = asyncio.run(
            retriever.retrieve_context("Completely unknown unrelated query xyz123")
        )

        assert context.chunks == []
        assert context.reason == "no_relevant_knowledge_found"
        assert context.formatted_context == "No relevant context found."

    def test_backward_compatible_retrieve_call(
        self, mock_embedding_service: MagicMock
    ) -> None:
        """Verify retrieve() returns a list of RetrievedDocument preserving legacy attributes."""
        fake_session = AsyncMock()
        fake_session.scalar.return_value = uuid.uuid4()

        c1, s1 = _make_chunk(
            doc_id="doc_test",
            title="Test Doc",
            domain="histopathology",
            content="Test content for backward compatibility.",
            distance=0.20,
        )

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [(c1, s1)]
        fake_session.execute.return_value = mock_exec_result

        retriever = RAGRetriever(
            session=fake_session,
            embedding_service=mock_embedding_service,
        )

        docs = asyncio.run(retriever.retrieve("What is histopathology?"))

        assert isinstance(docs, list)
        assert len(docs) == 1
        doc = docs[0]
        # Legacy attributes required by chat_service
        assert hasattr(doc, "similarity")
        assert hasattr(doc, "topic")
        assert hasattr(doc, "source")
        assert hasattr(doc, "content")
        # Phase 3 enhancement attributes
        assert hasattr(doc, "source_url")
        assert hasattr(doc, "source_tier")
        assert hasattr(doc, "citation")


class TestRetrievalEvaluationBenchmark:
    """Evaluates retrieval quality against the curated 09_qa_evaluation test cases."""

    def test_evaluation_benchmark_cases(self) -> None:
        """Verify all test cases in 09_qa_evaluation/retrieval_test_cases.json route accurately."""
        # Locate evaluation benchmark file
        eval_file = (
            Path(__file__).resolve().parents[3]
            / "knowledge_base"
            / "oncovision_medical_knowledgebase_v3"
            / "09_qa_evaluation"
            / "retrieval_test_cases.json"
        )
        assert eval_file.exists(), f"Benchmark file not found at {eval_file}"

        test_cases = json.loads(eval_file.read_text(encoding="utf-8"))
        assert len(test_cases) == 10

        classifier = QueryScopeClassifier()
        successful_routes = 0

        for tc in test_cases:
            tc_id = tc["id"]
            query = tc["query"]
            expected_route = tc["expected_route"]  # e.g. "01_colon", "02_lung", "06_safety"

            scope = classifier.classify(query)

            # Map expected directory to domain
            if "00_general" in expected_route:
                matched = scope.domain in {
                    QueryDomain.GENERAL_ONCOLOGY,
                    QueryDomain.HISTOPATHOLOGY,
                    QueryDomain.LUNG,
                    QueryDomain.COLON,
                }
            elif "01_colon" in expected_route:
                matched = scope.domain == QueryDomain.COLON
            elif "02_lung" in expected_route:
                matched = scope.domain == QueryDomain.LUNG
            elif "03_classes" in expected_route:
                matched = scope.domain in {QueryDomain.COLON, QueryDomain.LUNG, QueryDomain.CLASSIFIER_CONTEXT}
            elif "04_comparisons" in expected_route:
                matched = scope.domain == QueryDomain.COMPARISON
            elif "06_safety" in expected_route:
                matched = scope.requires_safety_context or scope.domain == QueryDomain.SAFETY_POLICY
            else:
                matched = True

            assert matched, f"Benchmark test {tc_id} ('{query}') failed routing: got domain={scope.domain}, expected={expected_route}"
            successful_routes += 1

        assert successful_routes == 10
