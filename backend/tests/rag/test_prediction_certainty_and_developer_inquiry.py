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
    """'who build you?' is detected as an explicit developer query."""
    q = "who build you?"
    assert is_explicit_developer_query(q) is True
    scope = classifier.classify(q)
    assert scope.intent == QueryIntent.CLASSIFIER_EXPLANATION
    assert scope.domain == QueryDomain.DEVELOPER_INFO


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

