"""Reproducible automated test suite for Clinical Chatbot Question Diversity & Retrieval Debugging.

Covers 35 distinct clinical questions across Categories A through H:
A. General oncology (4 questions)
B. Colon histopathology (4 questions)
C. Lung histopathology (4 questions)
D. Biomarkers and immunohistochemistry (3 questions)
E. Staging and treatment boundaries (3 questions)
F. Classifier and prediction interpretation (7 questions)
G. Actual prediction-history questions (5 questions)
H. Ambiguous, unsupported, and adversarial questions (5 questions)

Verifies routing, retrieval candidates, grounding decisions, and response generation without hardcoding answers.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.history.summary import PredictionHistorySummary
from app.models.knowledge_embedding import KnowledgeEmbedding
from app.rag.classifier import (
    ClassScope,
    QueryDomain,
    QueryIntent,
    QueryScope,
    QueryScopeClassifier,
)
from app.rag.generator import GroundedRAGGenerator
from app.rag.grounding import GroundingEvaluator
from app.rag.retriever import RAGRetriever, RetrievedContext, RetrievedDocument


def _make_chunk(
    doc_id: str,
    title: str,
    domain: str,
    content: str,
    class_scope: str | list[str] | None = None,
    source_url: str = "https://www.cancer.gov/types/lung",
    source_title: str = "NCI Clinical Oncology",
    source_tier: int = 1,
    similarity: float = 0.88,
) -> tuple[KnowledgeEmbedding, float]:
    rec = MagicMock(spec=KnowledgeEmbedding)
    rec.id = uuid.uuid4()
    rec.document_id = doc_id
    rec.document_title = title
    rec.domain = domain
    rec.topic = domain
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
    return rec, similarity


@pytest.fixture
def classifier() -> QueryScopeClassifier:
    return QueryScopeClassifier()


@pytest.fixture
def grounding_evaluator() -> GroundingEvaluator:
    return GroundingEvaluator()


@pytest.fixture
def real_test_prediction_summary() -> PredictionHistorySummary:
    """Real prediction summary matching the authorized production test record."""
    return PredictionHistorySummary(
        predicted_class="unknown",
        confidence=0.5032,
        agreement_ratio=0.50,
        participating_models=2,
        successful_models=["mobilenetv2", "densenet121"],
        failed_models=[],
    )


class TestCategoryARoutingAndRetrieval:
    """Category A: General oncology questions."""

    @pytest.mark.parametrize(
        "query,expected_domain,expected_intent",
        [
            ("What is cancer?", QueryDomain.GENERAL_ONCOLOGY, QueryIntent.GENERAL_KNOWLEDGE),
            ("What is the difference between benign and malignant tumors?", QueryDomain.COMPARISON, QueryIntent.COMPARISON),
            ("What does carcinoma mean?", QueryDomain.GENERAL_ONCOLOGY, QueryIntent.GENERAL_KNOWLEDGE),
            ("How does cancer differ from normal tissue?", QueryDomain.COMPARISON, QueryIntent.COMPARISON),
        ],
    )
    def test_general_oncology_routing(
        self,
        classifier: QueryScopeClassifier,
        query: str,
        expected_domain: QueryDomain,
        expected_intent: QueryIntent,
    ) -> None:
        scope = classifier.classify(query)
        assert scope.domain == expected_domain
        assert scope.intent == expected_intent
        # General oncology questions must not be forced into a narrow LC25000 classifier class
        assert scope.class_scopes == []


class TestCategoryBColonHistopathology:
    """Category B: Colon histopathology questions."""

    @pytest.mark.parametrize(
        "query,expected_domain,expected_intent,expected_classes",
        [
            ("What is colon adenocarcinoma?", QueryDomain.COLON, QueryIntent.CLASS_EXPLANATION, [ClassScope.COLON_ADENOCARCINOMA]),
            ("What histological features characterize colon adenocarcinoma?", QueryDomain.COLON, QueryIntent.HISTOPATHOLOGY, [ClassScope.COLON_ADENOCARCINOMA]),
            ("How is benign colonic tissue different from colon adenocarcinoma?", QueryDomain.COMPARISON, QueryIntent.COMPARISON, [ClassScope.COLON_ADENOCARCINOMA, ClassScope.BENIGN_COLONIC_TISSUE]),
            ("What does glandular differentiation mean?", QueryDomain.HISTOPATHOLOGY, QueryIntent.HISTOPATHOLOGY, []),
        ],
    )
    def test_colon_histopathology_routing(
        self,
        classifier: QueryScopeClassifier,
        query: str,
        expected_domain: QueryDomain,
        expected_intent: QueryIntent,
        expected_classes: list[ClassScope],
    ) -> None:
        scope = classifier.classify(query)
        assert scope.domain == expected_domain
        assert scope.intent == expected_intent
        assert set(scope.class_scopes) == set(expected_classes)


class TestCategoryCLungHistopathology:
    """Category C: Lung histopathology questions."""

    @pytest.mark.parametrize(
        "query,expected_domain,expected_intent,expected_classes",
        [
            ("What is lung adenocarcinoma?", QueryDomain.LUNG, QueryIntent.CLASS_EXPLANATION, [ClassScope.LUNG_ADENOCARCINOMA]),
            ("What does lepidic growth mean?", QueryDomain.LUNG, QueryIntent.HISTOPATHOLOGY, [ClassScope.LUNG_ADENOCARCINOMA]),
            ("How does lung adenocarcinoma differ from lung squamous cell carcinoma?", QueryDomain.COMPARISON, QueryIntent.COMPARISON, [ClassScope.LUNG_ADENOCARCINOMA, ClassScope.LUNG_SQUAMOUS_CELL_CARCINOMA]),
            ("What are the limitations of identifying a lung cancer subtype from morphology alone?", QueryDomain.LUNG, QueryIntent.HISTOPATHOLOGY, []),
        ],
    )
    def test_lung_histopathology_routing(
        self,
        classifier: QueryScopeClassifier,
        query: str,
        expected_domain: QueryDomain,
        expected_intent: QueryIntent,
        expected_classes: list[ClassScope],
    ) -> None:
        scope = classifier.classify(query)
        assert scope.domain == expected_domain
        assert scope.intent == expected_intent
        assert set(scope.class_scopes) == set(expected_classes)


class TestCategoryDBiomarkersAndIHC:
    """Category D: Biomarkers and Immunohistochemistry."""

    @pytest.mark.parametrize(
        "query,expected_domain,expected_intent,expected_safety",
        [
            ("Can an H&E image prove an EGFR mutation?", QueryDomain.LUNG, QueryIntent.BIOMARKER, True),
            ("What is p40 used for in lung pathology?", QueryDomain.LUNG, QueryIntent.IMMUNOHISTOCHEMISTRY, False),
            ("What is the difference between histological classification and molecular testing?", QueryDomain.COMPARISON, QueryIntent.COMPARISON, False),
        ],
    )
    def test_biomarkers_routing(
        self,
        classifier: QueryScopeClassifier,
        query: str,
        expected_domain: QueryDomain,
        expected_intent: QueryIntent,
        expected_safety: bool,
    ) -> None:
        scope = classifier.classify(query)
        assert scope.domain == expected_domain
        assert scope.intent == expected_intent
        assert scope.requires_safety_context == expected_safety


class TestCategoryEStagingAndTreatmentBoundaries:
    """Category E: Staging and treatment boundaries."""

    @pytest.mark.parametrize(
        "query,expected_domain,expected_intent,expected_safety",
        [
            ("Can a histopathology image alone determine the complete cancer stage?", QueryDomain.SAFETY_POLICY, QueryIntent.STAGING, True),
            ("What information may be needed for cancer staging?", QueryDomain.GENERAL_ONCOLOGY, QueryIntent.STAGING, False),
            ("Can this chatbot recommend a personalized chemotherapy regimen?", QueryDomain.SAFETY_POLICY, QueryIntent.TREATMENT, True),
        ],
    )
    def test_staging_treatment_routing(
        self,
        classifier: QueryScopeClassifier,
        query: str,
        expected_domain: QueryDomain,
        expected_intent: QueryIntent,
        expected_safety: bool,
    ) -> None:
        scope = classifier.classify(query)
        assert scope.domain == expected_domain
        assert scope.intent == expected_intent
        assert scope.requires_safety_context == expected_safety


class TestCategoryFClassifierInterpretation:
    """Category F: Classifier and prediction interpretation questions."""

    @pytest.mark.parametrize(
        "query",
        [
            "What does the predicted class mean?",
            "What does model confidence mean?",
            "Does 99% model confidence mean a 99% probability that the patient has cancer?",
            "What does 100% agreement between participating models mean?",
            "Are you sure this prediction refers to cancer?",
            "Why might two models disagree?",
            "Can this prediction be treated as a confirmed clinical diagnosis?",
        ],
    )
    def test_classifier_interpretation_routing(
        self,
        classifier: QueryScopeClassifier,
        query: str,
    ) -> None:
        scope = classifier.classify(query)
        assert scope.intent == QueryIntent.CLASSIFIER_EXPLANATION
        assert scope.domain == QueryDomain.CLASSIFIER_CONTEXT


class TestCategoryGActualPredictionHistory:
    """Category G: Actual prediction history queries with verified prediction summary."""

    @pytest.mark.parametrize(
        "query",
        [
            "What class did my latest prediction return?",
            "What confidence did the system report?",
            "Did all participating models agree?",
            "Which individual models disagreed, if any?",
            "Explain my prediction using the medical knowledgebase.",
        ],
    )
    def test_prediction_history_routing(
        self,
        classifier: QueryScopeClassifier,
        query: str,
    ) -> None:
        scope = classifier.classify(query)
        assert scope.intent == QueryIntent.CLASSIFIER_EXPLANATION
        assert scope.domain == QueryDomain.CLASSIFIER_CONTEXT

    def test_prediction_history_grounding_with_record(
        self,
        grounding_evaluator: GroundingEvaluator,
        classifier: QueryScopeClassifier,
        real_test_prediction_summary: PredictionHistorySummary,
    ) -> None:
        query = "What confidence did the system report?"
        scope = classifier.classify(query)
        ctx = RetrievedContext(chunks=[], query_scope=scope, reason="empty_knowledge_base")

        decision = grounding_evaluator.evaluate(
            query=query,
            context=ctx,
            prediction_summary=real_test_prediction_summary,
        )
        assert decision.is_eligible is True
        assert decision.decision_reason == "classifier_prediction_context"

    def test_prediction_history_grounding_without_record_returns_informative_guidance(
        self,
        grounding_evaluator: GroundingEvaluator,
        classifier: QueryScopeClassifier,
    ) -> None:
        query = "What class did my latest prediction return?"
        scope = classifier.classify(query)
        ctx = RetrievedContext(chunks=[], query_scope=scope, reason="empty_knowledge_base")

        decision = grounding_evaluator.evaluate(
            query=query,
            context=ctx,
            prediction_summary=None,
        )
        assert decision.is_eligible is True
        assert decision.decision_reason == "no_active_prediction"


class TestCategoryHAmbiguousAndAdversarial:
    """Category H: Ambiguous, unsupported, and adversarial questions."""

    def test_vague_question_routes_to_general(self, classifier: QueryScopeClassifier) -> None:
        scope = classifier.classify("Tell me about cancer.")
        assert scope.domain == QueryDomain.GENERAL_ONCOLOGY
        assert scope.intent == QueryIntent.GENERAL_KNOWLEDGE

    def test_unrelated_question_routes_out_of_domain(
        self,
        classifier: QueryScopeClassifier,
        grounding_evaluator: GroundingEvaluator,
    ) -> None:
        query = "What is the capital of France?"
        scope = classifier.classify(query)
        assert scope.domain is None

        # Low-similarity candidate from dense background
        cand, sim = _make_chunk(
            doc_id="doc_lung",
            title="Lung Pathology",
            domain="lung",
            content="Lung tissue structure.",
            similarity=0.55,
        )
        doc = RetrievedDocument(
            content=cand.content,
            source=cand.source,
            topic=cand.topic,
            similarity=sim,
            document_id=cand.document_id,
        )
        ctx = RetrievedContext(chunks=[doc], query_scope=scope, reason="success")

        decision = grounding_evaluator.evaluate(query=query, context=ctx)
        assert decision.is_eligible is False
        assert decision.decision_reason == "out_of_domain_query"

    @pytest.mark.anyio
    async def test_out_of_domain_receives_differentiated_fallback(
        self,
        classifier: QueryScopeClassifier,
    ) -> None:
        generator = GroundedRAGGenerator()
        query = "What is the capital of France?"
        scope = classifier.classify(query)

        # Empty or weak retrieval
        ctx = RetrievedContext(chunks=[], query_scope=scope, reason="no_relevant_knowledge_found")
        answer = await generator.generate_grounded_answer(query=query, context=ctx)

        assert answer.grounded is False
        assert answer.refusal_reason in {"no_relevant_knowledge_found", "out_of_domain_query", "empty_retrieval"}
        assert len(answer.citations) == 0
        assert "enough relevant information" in answer.answer or "limited information" in answer.answer

    @pytest.mark.parametrize(
        "query",
        [
            "I disagree with this argument",
            "Why did they disagree?",
            "I disagreed with the proposed architecture",
        ],
    )
    def test_unrelated_disagreement_must_not_route_to_classifier_context(
        self,
        classifier: QueryScopeClassifier,
        query: str,
    ) -> None:
        scope = classifier.classify(query)
        assert scope.domain != QueryDomain.CLASSIFIER_CONTEXT
        assert scope.domain is None
        assert scope.intent != QueryIntent.CLASSIFIER_EXPLANATION
        assert scope.intent == QueryIntent.GENERAL_KNOWLEDGE

    @pytest.mark.parametrize(
        "query",
        [
            "Which individual models disagreed, if any?",
            "Which models disagree on this prediction?",
        ],
    )
    def test_model_disagreement_must_preserve_classifier_context_routing(
        self,
        classifier: QueryScopeClassifier,
        query: str,
    ) -> None:
        scope = classifier.classify(query)
        assert scope.domain == QueryDomain.CLASSIFIER_CONTEXT
        assert scope.intent == QueryIntent.CLASSIFIER_EXPLANATION


class TestMultiClassComparisonRetrievalDiversity:
    """Verifies that comparison queries retrieve balanced candidates for both classes."""

    def test_dual_class_comparison_retriever_diversity(self) -> None:
        fake_session = AsyncMock()
        mock_emb = MagicMock()
        mock_emb.get_embedding = AsyncMock(return_value=[0.05] * 768)

        retriever = RAGRetriever(
            session=fake_session,
            embedding_service=mock_emb,
        )

        c_adeno1, s1 = _make_chunk(
            doc_id="lung_adeno_doc",
            title="Lung Adeno 1",
            domain="lung",
            content="Glandular patterns and TTF1 positivity.",
            class_scope="lung_adenocarcinoma",
            similarity=0.88,
        )
        c_adeno2, s2 = _make_chunk(
            doc_id="lung_adeno_doc_2",
            title="Lung Adeno 2",
            domain="lung",
            content="Lepidic growth along alveolar walls.",
            class_scope="lung_adenocarcinoma",
            similarity=0.87,
        )
        c_sqcc1, s3 = _make_chunk(
            doc_id="lung_sqcc_doc",
            title="Lung SqCC 1",
            domain="lung",
            content="Keratinization and p40 positivity.",
            class_scope="lung_squamous_cell_carcinoma",
            similarity=0.85,
        )

        candidates = [(c_adeno1, s1), (c_adeno2, s2), (c_sqcc1, s3)]

        scope = QueryScope(
            domain=QueryDomain.COMPARISON,
            class_scopes=[ClassScope.LUNG_ADENOCARCINOMA, ClassScope.LUNG_SQUAMOUS_CELL_CARCINOMA],
            intent=QueryIntent.COMPARISON,
            confidence=0.98,
        )

        ranked = retriever._rerank_and_diversify(
            candidates=candidates,
            query_scope=scope,
            top_k=2,
        )

        assert len(ranked) == 2
        classes_represented = {doc.class_scope for doc in ranked}
        assert "lung_adenocarcinoma" in classes_represented
        assert "lung_squamous_cell_carcinoma" in classes_represented
