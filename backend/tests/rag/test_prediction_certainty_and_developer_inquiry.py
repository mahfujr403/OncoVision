"""Tests for prediction certainty explanations and developer inquiries in prediction chat.

Validates:
1. Classification of certainty queries ('are you sure about this prediction?') as CLASSIFIER_EXPLANATION / CLASSIFIER_CONTEXT.
2. Classification of developer queries ('who build you?') as explicit developer inquiries.
3. Grounding eligibility for prediction certainty based on PredictionHistorySummary.
4. Grounding eligibility for developer inquiries without requiring medical literature similarity.
5. End-to-end generator responses without false RAG refusals.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.history.summary import PredictionHistorySummary
from app.rag.classifier import (
    QueryDomain,
    QueryIntent,
    QueryScope,
    QueryScopeClassifier,
)
from app.rag.generator import GroundedRAGGenerator
from app.rag.grounding import GroundingEvaluator
from app.rag.provenance import is_explicit_developer_query
from app.rag.retriever import RetrievedContext, RetrievedDocument


@pytest.fixture
def classifier() -> QueryScopeClassifier:
    return QueryScopeClassifier()


@pytest.fixture
def grounding_evaluator() -> GroundingEvaluator:
    return GroundingEvaluator()


@pytest.fixture
def sample_prediction_summary() -> PredictionHistorySummary:
    return PredictionHistorySummary(
        predicted_class="colon_adenocarcinoma",
        confidence=0.9997,
        agreement_ratio=1.0,
        participating_models=2,
        successful_models=["DenseNet121", "EfficientNetV2B0_ResNet50_Fusion"],
        failed_models=[],
    )


def test_prediction_certainty_classification(classifier: QueryScopeClassifier):
    """'are you sure about this prediction?' maps to CLASSIFIER_EXPLANATION and CLASSIFIER_CONTEXT."""
    queries = [
        "are you sure about this prediction?",
        "how sure are you about this prediction?",
        "how confident is the model?",
        "why this prediction?",
        "what is the certainty of this prediction?",
        "can i trust this prediction?",
    ]
    for q in queries:
        scope = classifier.classify(q)
        assert scope.intent == QueryIntent.CLASSIFIER_EXPLANATION, f"Failed for {q}"
        assert scope.domain == QueryDomain.CLASSIFIER_CONTEXT, f"Failed domain for {q}"


def test_developer_inquiry_detection(classifier: QueryScopeClassifier):
    """Developer inquiries across all verb inflections and phrasings are detected as explicit developer queries."""
    queries = [
        "who develop you?",
        "who build you?",
        "who developed you?",
        "who built you?",
        "who create you?",
        "who created you?",
        "who make you?",
        "who made you?",
        "who design you?",
        "who designed you?",
        "who coded you?",
        "who programmed you?",
        "who is your developer?",
        "who is your creator?",
        "who's your developer?",
        "who developed oncovision?",
        "who develop oncovision?",
        "you are developed by whom?",
        "who are you built by?",
        "who is behind oncovision?",
    ]
    for q in queries:
        assert is_explicit_developer_query(q) is True, f"is_explicit_developer_query failed for '{q}'"
        scope = classifier.classify(q)
        assert scope.intent == QueryIntent.CLASSIFIER_EXPLANATION, f"Failed intent for '{q}'"
        assert scope.domain == QueryDomain.DEVELOPER_INFO, f"Failed domain for '{q}'"


def test_prediction_certainty_grounding_eligible(
    grounding_evaluator: GroundingEvaluator,
    classifier: QueryScopeClassifier,
    sample_prediction_summary: PredictionHistorySummary,
):
    """Certainty queries are eligible when prediction_summary is provided."""
    q = "are you sure about this prediction?"
    scope = classifier.classify(q)
    context = RetrievedContext(
        chunks=[],
        query_scope=scope,
        reason="no_relevant_knowledge_found",
    )
    decision = grounding_evaluator.evaluate(
        query=q,
        context=context,
        prediction_summary=sample_prediction_summary,
    )
    assert decision.is_eligible is True
    assert decision.decision_reason == "classifier_prediction_context"


def test_developer_inquiry_grounding_eligible(
    grounding_evaluator: GroundingEvaluator,
    classifier: QueryScopeClassifier,
):
    """Developer queries are eligible without requiring medical literature similarity."""
    q = "who build you?"
    scope = classifier.classify(q)
    context = RetrievedContext(
        chunks=[],
        query_scope=scope,
        reason="no_relevant_knowledge_found",
    )
    decision = grounding_evaluator.evaluate(
        query=q,
        context=context,
    )
    assert decision.is_eligible is True
    assert decision.decision_reason == "developer_query"


def test_generator_explains_prediction_certainty(
    classifier: QueryScopeClassifier,
    sample_prediction_summary: PredictionHistorySummary,
):
    """Generator accepts and grounds prediction certainty explanations on prediction_summary."""
    q = "are you sure about this prediction?"
    scope = classifier.classify(q)
    context = RetrievedContext(
        chunks=[],
        query_scope=scope,
        reason="prediction_context",
    )

    mock_client = MagicMock()
    mock_client.generate = AsyncMock(
        return_value=(
            "The OncoVision ensemble classifier predicted colon adenocarcinoma with 99.97% confidence "
            "and 100% agreement between participating architectures (DenseNet121 and EfficientNetV2B0_ResNet50_Fusion). "
            "While the model shows high statistical certainty, AI outputs are for clinical decision support "
            "and must always be validated by a board-certified pathologist."
        )
    )

    generator = GroundedRAGGenerator(llm_client=mock_client)
    ans = asyncio.run(
        generator.generate_grounded_answer(
            query=q,
            context=context,
            prediction_summary=sample_prediction_summary,
        )
    )

    assert ans.grounded is True
    assert "99.97%" in ans.answer
    assert "colon adenocarcinoma" in ans.answer
    assert "The available OncoVision knowledge base provides only limited information" not in ans.answer


def test_generator_answers_developer_inquiry():
    """Generator answers 'who build you?' without requiring citations or failing closed."""
    q = "who build you?"
    classifier = QueryScopeClassifier()
    scope = classifier.classify(q)
    context = RetrievedContext(
        chunks=[],
        query_scope=scope,
        reason="developer_context",
    )

    mock_client = MagicMock()
    mock_client.generate = AsyncMock(
        return_value=(
            "OncoVision AI was designed and developed by Md. Mahfujur Rahman, a Machine Learning Engineer and AI Researcher. "
            "His research focuses on deep learning architectures and multimodal feature fusion for cancer histopathology."
        )
    )

    generator = GroundedRAGGenerator(llm_client=mock_client)
    ans = asyncio.run(
        generator.generate_grounded_answer(
            query=q,
            context=context,
        )
    )

    assert ans.grounded is True
    assert "Md. Mahfujur Rahman" in ans.answer
    assert "The available OncoVision knowledge base provides only limited information" not in ans.answer


def test_generator_explains_no_active_prediction_gracefully():
    """When asked about prediction certainty without an active prediction, generator explains gracefully."""
    q = "are you sure about this prediction?"
    classifier = QueryScopeClassifier()
    scope = classifier.classify(q)
    context = RetrievedContext(
        chunks=[],
        query_scope=scope,
        reason="no_relevant_knowledge_found",
    )

    mock_client = MagicMock()
    generator = GroundedRAGGenerator(llm_client=mock_client)
    ans = asyncio.run(
        generator.generate_grounded_answer(
            query=q,
            context=context,
            prediction_summary=None,
        )
    )

    assert ans.grounded is True
    assert "There is no active histopathology slide evaluation" in ans.answer
    assert "The available OncoVision knowledge base provides only limited information" not in ans.answer


def test_generator_answers_contact_info_request():
    """Generator answers 'Can you give me his contact information?' with verified public links."""
    q = "Can you give me his contact information?"
    classifier = QueryScopeClassifier()
    scope = classifier.classify(q)
    assert scope.domain == QueryDomain.DEVELOPER_INFO
    assert is_explicit_developer_query(q) is True

    context = RetrievedContext(
        chunks=[],
        query_scope=scope,
        reason="developer_context",
    )

    mock_client = MagicMock()
    mock_client.generate = AsyncMock(
        return_value=(
            "You can contact the developer of OncoVision AI, Md. Mahfujur Rahman, through his verified public channels:\n"
            "- Email: mahfujr403@gmail.com\n"
            "- Portfolio: https://md-mahfujur-rahman.vercel.app/\n"
            "- GitHub: https://github.com/mahfujr403\n"
            "- LinkedIn: https://linkedin.com/in/mahfujr403\n"
            "- Project Repository: https://github.com/mahfujr403/OncoVision\n"
            "Please note that private contact information such as phone numbers or home addresses are unavailable."
        )
    )

    generator = GroundedRAGGenerator(llm_client=mock_client)
    ans = asyncio.run(
        generator.generate_grounded_answer(
            query=q,
            context=context,
        )
    )

    assert ans.grounded is True
    assert "mahfujr403@gmail.com" in ans.answer
    assert "md-mahfujur-rahman.vercel.app" in ans.answer
    assert "github.com/mahfujr403" in ans.answer
    assert "phone numbers" in ans.answer.lower() or "unavailable" in ans.answer.lower()


def test_demonstrative_query_classification(classifier: QueryScopeClassifier):
    """Demonstrative inquiries about the active case/prediction map to CLASSIFIER_EXPLANATION."""
    queries = [
        "this is a cancer?",
        "is this cancer?",
        "if i supposed to that is surely a cancer?",
        "is this surely a cancer?",
        "is this benign or malignant?",
        "does this mean cancer?",
        "is that cancer?",
        "can this be cancer?",
        "এটা কি ক্যান্সার?",
        "এটা কি নিশ্চিত ক্যান্সার?",
    ]
    for q in queries:
        scope = classifier.classify(q)
        assert scope.intent == QueryIntent.CLASSIFIER_EXPLANATION, f"Failed intent for '{q}'"
        assert scope.domain == QueryDomain.CLASSIFIER_CONTEXT, f"Failed domain for '{q}'"


def test_demonstrative_query_grounding(
    grounding_evaluator: GroundingEvaluator,
    classifier: QueryScopeClassifier,
    sample_prediction_summary: PredictionHistorySummary,
):
    """Demonstrative queries are grounded in active prediction, or report no_active_prediction if missing."""
    queries = [
        "this is a cancer?",
        "if i supposed to that is surely a cancer?",
        "is this benign or malignant?",
    ]
    for q in queries:
        scope = classifier.classify(q)
        ctx = RetrievedContext(chunks=[], query_scope=scope, reason="no_relevant_knowledge_found")

        # With active prediction summary
        decision_with_pred = grounding_evaluator.evaluate(
            query=q,
            context=ctx,
            prediction_summary=sample_prediction_summary,
        )
        assert decision_with_pred.is_eligible is True, f"Failed eligibility with pred for '{q}'"
        assert decision_with_pred.decision_reason == "classifier_prediction_context", f"Wrong reason for '{q}'"

        # Without active prediction summary
        decision_without_pred = grounding_evaluator.evaluate(
            query=q,
            context=ctx,
            prediction_summary=None,
        )
        assert decision_without_pred.is_eligible is True, f"Failed eligibility without pred for '{q}'"
        assert decision_without_pred.decision_reason == "no_active_prediction", f"Wrong reason without pred for '{q}'"


def test_generator_answers_demonstrative_cancer_inquiry(
    classifier: QueryScopeClassifier,
    sample_prediction_summary: PredictionHistorySummary,
):
    """Generator answers 'this is a cancer?' using active prediction context without falling back."""
    q = "this is a cancer?"
    scope = classifier.classify(q)
    context = RetrievedContext(
        chunks=[],
        query_scope=scope,
        reason="prediction_context",
    )

    mock_client = MagicMock()
    mock_client.generate = AsyncMock(
        return_value=(
            "Yes, Colon Adenocarcinoma is a malignant epithelial neoplasm (cancer) originating in the glandular "
            "epithelium of the colon. The OncoVision system classified the analyzed slide as Colon Adenocarcinoma "
            "with 99.97% ensemble confidence and 100% agreement across participating models. "
            "Please note that this algorithmic prediction represents statistical ensemble probability, "
            "not a confirmed clinical diagnosis; definitive clinical confirmation requires histological evaluation by a qualified pathologist."
        )
    )

    generator = GroundedRAGGenerator(llm_client=mock_client)
    ans = asyncio.run(
        generator.generate_grounded_answer(
            query=q,
            context=context,
            prediction_summary=sample_prediction_summary,
        )
    )

    assert ans.grounded is True
    assert "Colon Adenocarcinoma" in ans.answer
    assert "99.97%" in ans.answer
    assert "The available OncoVision knowledge base provides only limited information" not in ans.answer
