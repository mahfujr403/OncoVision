"""Focused unit tests for Phase 5.1 Deterministic Grounding & Relevance Evaluation.

Tests:
- Strong relevant retrieval -> eligible=True, grounded=True
- Weak relevant retrieval -> eligible=False, grounded=False
- Irrelevant non-empty retrieval -> eligible=False, grounded=False
- Empty retrieval -> eligible=False, grounded=False
- Safety refusal -> eligible=False, grounded=False
- Domain & class mismatch handling
- Generator conservative refusal behavior on ineligible retrieval
- Prediction history immutability
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.settings import get_settings
from app.history.summary import PredictionHistorySummary
from app.rag.classifier import (
    ClassScope,
    QueryDomain,
    QueryIntent,
    QueryScope,
    QueryScopeClassifier,
)
from app.rag.generator import GroundedRAGGenerator
from app.rag.grounding import GroundingDecision, GroundingEvaluator
from app.rag.retriever import RetrievedContext, RetrievedDocument
from app.rag.safety import SafetyBoundary, SafetyEvaluation, SafetyEvaluator
from app.rag.schemas import GroundedAnswer


def make_test_chunk(
    doc_id: str,
    title: str,
    similarity: float,
    domain: str,
    content: str = "Medical evidence content.",
    topic: str = "pathology",
) -> RetrievedDocument:
    return RetrievedDocument(
        content=content,
        source=f"{domain}/{doc_id}.md",
        topic=topic,
        similarity=similarity,
        document_id=doc_id,
        document_title=title,
        domain=domain,
        source_title=title,
        source_url=f"https://example.org/{doc_id}",
        source_tier=2,
    )


class TestGroundingEvaluator:
    """Unit tests for GroundingEvaluator gate logic."""

    @pytest.fixture(autouse=True)
    def setup_evaluator(self):
        self.settings = get_settings()
        self.evaluator = GroundingEvaluator(self.settings)

    def test_strong_relevant_retrieval_is_eligible(self):
        """Relevant medical query with high similarity and matching domain must pass."""
        scope = QueryScope(
            domain=QueryDomain.LUNG,
            class_scopes=[ClassScope.LUNG_ADENOCARCINOMA],
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=0.95,
        )
        context = RetrievedContext(
            chunks=[
                make_test_chunk("lung_1", "Lung Adeno Morphology", 0.94, "lung", topic="lung_adenocarcinoma"),
                make_test_chunk("lung_2", "Lung IHC Markers", 0.91, "lung", topic="lung_adenocarcinoma"),
            ],
            query_scope=scope,
            reason="success",
        )

        decision = self.evaluator.evaluate(
            query="What are the histologic hallmarks of lung adenocarcinoma?",
            context=context,
        )

        assert decision.is_eligible is True
        assert decision.decision_reason == "relevant_retrieval"
        assert decision.top_similarity == 0.94
        assert decision.domain_compatible is True

    def test_weak_relevant_retrieval_is_not_eligible(self):
        """Relevant medical query with low similarity (below 0.75 floor) must be rejected."""
        scope = QueryScope(
            domain=QueryDomain.GENERAL_ONCOLOGY,
            intent=QueryIntent.GENERAL_KNOWLEDGE,
            confidence=0.90,
        )
        context = RetrievedContext(
            chunks=[
                make_test_chunk("general_1", "Tumor Biology", 0.68, "general_oncology"),
            ],
            query_scope=scope,
            reason="success",
        )

        decision = self.evaluator.evaluate(
            query="What are the molecular subtypes of glioblastoma multiforme?",
            context=context,
        )

        assert decision.is_eligible is False
        assert decision.decision_reason == "insufficient_similarity"
        assert decision.top_similarity == 0.68

    def test_irrelevant_query_with_background_chunks_is_not_eligible(self):
        """Unclassified out-of-domain query with weak semantic match must be rejected."""
        scope = QueryScope(
            domain=None,
            class_scopes=[],
            intent=QueryIntent.GENERAL_KNOWLEDGE,
            confidence=0.50,
        )
        # Background similarities in dense vector space typically hover around 0.55-0.65
        context = RetrievedContext(
            chunks=[
                make_test_chunk("normal_lung", "Normal Lung Microanatomy", 0.63, "lung"),
                make_test_chunk("normal_colon", "Normal Colon Microanatomy", 0.58, "colon"),
            ],
            query_scope=scope,
            reason="success",
        )

        decision = self.evaluator.evaluate(
            query="How do I configure an nginx reverse proxy for WebSockets?",
            context=context,
        )

        assert decision.is_eligible is False
        assert decision.decision_reason == "out_of_domain_query"
        assert decision.top_similarity == 0.63

    def test_empty_retrieval_is_not_eligible(self):
        """Empty chunks must be rejected immediately."""
        scope = QueryScope(domain=None, confidence=0.0)
        context = RetrievedContext(
            chunks=[],
            query_scope=scope,
            reason="no_relevant_knowledge_found",
        )

        decision = self.evaluator.evaluate(
            query="Random query with no matches",
            context=context,
        )

        assert decision.is_eligible is False
        assert decision.decision_reason == "empty_retrieval"
        assert decision.top_similarity == 0.0

    def test_safety_refusal_is_not_eligible(self):
        """Pre-generation safety refusal must yield ineligible grounding decision."""
        scope = QueryScope(domain=None, intent=QueryIntent.TREATMENT, confidence=0.90)
        context = RetrievedContext(
            chunks=[make_test_chunk("treatment_1", "Treatment Concepts", 0.77, "general_oncology")],
            query_scope=scope,
            reason="success",
        )
        safety_eval = SafetyEvaluation(
            boundary=SafetyBoundary.TREATMENT,
            requires_deterministic_refusal=True,
            refusal_message="Cannot prescribe medication.",
        )

        decision = self.evaluator.evaluate(
            query="What chemotherapy should I personally take?",
            context=context,
            safety_eval=safety_eval,
        )

        assert decision.is_eligible is False
        assert decision.decision_reason == SafetyBoundary.TREATMENT.value

    def test_domain_mismatch_is_not_eligible(self):
        """Query for colon pathology retrieving strictly unrelated lung chunks must fail domain check."""
        scope = QueryScope(
            domain=QueryDomain.COLON,
            class_scopes=[ClassScope.COLON_ADENOCARCINOMA],
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=0.95,
        )
        # Chunks are solely from lung
        context = RetrievedContext(
            chunks=[
                make_test_chunk("lung_1", "Lung Adeno Morphology", 0.88, "lung"),
            ],
            query_scope=scope,
            reason="success",
        )

        # Force a custom compatibility map where lung is not compatible with colon
        decision = self.evaluator.evaluate(
            query="What are the histological features of colon adenocarcinoma?",
            context=context,
        )

        # Chunks are lung, query is COLON -> colon compatibility set does not include lung
        assert decision.is_eligible is False
        assert decision.decision_reason == "domain_mismatch"
        assert decision.domain_compatible is False


class TestGeneratorGroundingIntegration:
    """Integration tests verifying GroundedRAGGenerator with GroundingEvaluator."""

    def test_irrelevant_query_returns_conservative_refusal_and_no_grounding(self):
        """Irrelevant query with non-empty background chunks must return conservative refusal and grounded=False."""
        async def _run():
            mock_client = MagicMock()
            generator = GroundedRAGGenerator(llm_client=mock_client)

            scope = QueryScope(domain=None, intent=QueryIntent.GENERAL_KNOWLEDGE, confidence=0.50)
            context = RetrievedContext(
                chunks=[
                    make_test_chunk("lung_doc", "Normal Lung", 0.62, "lung"),
                ],
                query_scope=scope,
                reason="success",
            )

            result = await generator.generate_grounded_answer(
                query="What is the recipe for baking French bread?",
                context=context,
            )

            assert isinstance(result, GroundedAnswer)
            assert result.grounded is False
            assert result.refusal_reason == "out_of_domain_query"
            assert len(result.citations) == 0
            assert "The available OncoVision knowledge base provides only limited information" in result.answer
            # LLM must not be called when retrieval is ineligible
            mock_client.generate.assert_not_called()

        asyncio.run(_run())

    def test_weak_retrieval_returns_conservative_refusal_and_no_grounding(self):
        """Medical query with weak similarity (< 0.75) must return conservative refusal without calling LLM."""
        async def _run():
            mock_client = MagicMock()
            generator = GroundedRAGGenerator(llm_client=mock_client)

            scope = QueryScope(domain=QueryDomain.GENERAL_ONCOLOGY, intent=QueryIntent.GENERAL_KNOWLEDGE, confidence=0.85)
            context = RetrievedContext(
                chunks=[
                    make_test_chunk("onc_doc", "General Oncology", 0.69, "general_oncology"),
                ],
                query_scope=scope,
                reason="success",
            )

            result = await generator.generate_grounded_answer(
                query="What is cutaneous melanoma Breslow depth?",
                context=context,
            )

            assert result.grounded is False
            assert result.refusal_reason == "insufficient_similarity"
            assert len(result.citations) == 0
            assert "The available OncoVision knowledge base provides only limited information" in result.answer
            mock_client.generate.assert_not_called()

        asyncio.run(_run())

    def test_strong_relevant_retrieval_calls_llm_and_sets_grounded_true(self):
        """Relevant query with strong similarity (>= 0.75) calls LLM and returns grounded=True with citations."""
        async def _run():
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="Lung adenocarcinoma shows acinar and lepidic patterns [S1]."
            )
            generator = GroundedRAGGenerator(llm_client=mock_client)

            scope = QueryScope(
                domain=QueryDomain.LUNG,
                class_scopes=[ClassScope.LUNG_ADENOCARCINOMA],
                intent=QueryIntent.HISTOPATHOLOGY,
                confidence=0.95,
            )
            context = RetrievedContext(
                chunks=[
                    make_test_chunk("lung_adeno", "Lung Adeno", 0.94, "lung", topic="lung_adenocarcinoma"),
                ],
                query_scope=scope,
                reason="success",
            )

            result = await generator.generate_grounded_answer(
                query="What are the histologic hallmarks of lung adenocarcinoma?",
                context=context,
            )

            assert result.grounded is True
            assert result.refusal_reason is None
            assert len(result.citations) == 1
            assert result.citations[0].source_id == "S1"
            mock_client.generate.assert_called_once()

        asyncio.run(_run())

    def test_prediction_summary_immutability(self):
        """PredictionHistorySummary attributes must remain immutable through generation."""
        async def _run():
            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="The model classified the patch as lung adenocarcinoma based on glandular features [S1]."
            )
            generator = GroundedRAGGenerator(llm_client=mock_client)

            summary = PredictionHistorySummary(
                predicted_class="lung_adenocarcinoma",
                confidence=0.965,
                agreement_ratio=1.0,
                successful_models=["DenseNet121", "MobileNetV2", "FeatureFusion"],
                participating_models=3,
            )

            scope = QueryScope(domain=QueryDomain.LUNG, intent=QueryIntent.GENERAL_KNOWLEDGE, confidence=0.90)
            context = RetrievedContext(
                chunks=[
                    make_test_chunk("lung_adeno", "Lung Adeno", 0.93, "lung"),
                ],
                query_scope=scope,
                reason="success",
            )

            result = await generator.generate_grounded_answer(
                query="Why did the model predict this class?",
                context=context,
                prediction_summary=summary,
            )

            assert result.grounded is True
            # Assert summary fields unchanged
            assert summary.predicted_class == "lung_adenocarcinoma"
            assert summary.confidence == 0.965
            assert summary.agreement_ratio == 1.0
            assert summary.participating_models == 3

        asyncio.run(_run())
