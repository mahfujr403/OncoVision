"""Unit tests for QueryScopeClassifier and strict typed output schema (Phase 3).

Verifies:
1. Strict typed output schema and enum constraints (QueryDomain, ClassScope, QueryIntent).
2. Canonical Examples A through H from Phase 3 specification.
3. IHC, benign tissue, biomarker, staging, and treatment routing.
4. Conservative detection: ambiguous queries return domain=None or broader scope without forcing classes.
5. Scope classification confidence is bounded in [0.0, 1.0].
6. Explicit class matching is True only when classes are explicitly named.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.rag.classifier import (
    ClassScope,
    QueryDomain,
    QueryIntent,
    QueryScope,
    QueryScopeClassifier,
)


@pytest.fixture
def classifier() -> QueryScopeClassifier:
    """Fixture providing QueryScopeClassifier instance."""
    return QueryScopeClassifier()


class TestQueryScopeSchema:
    """Tests asserting the strict typed schema and enum constraints."""

    def test_schema_valid_instantiation(self) -> None:
        """Verify QueryScope can be instantiated with valid fields."""
        scope = QueryScope(
            domain=QueryDomain.LUNG,
            class_scopes=[ClassScope.LUNG_ADENOCARCINOMA],
            intent=QueryIntent.HISTOPATHOLOGY,
            confidence=0.94,
            explicit_class_match=True,
            requires_safety_context=False,
        )

        assert scope.domain == QueryDomain.LUNG
        assert scope.class_scopes == [ClassScope.LUNG_ADENOCARCINOMA]
        assert scope.class_scope == ClassScope.LUNG_ADENOCARCINOMA
        assert scope.intent == QueryIntent.HISTOPATHOLOGY
        assert scope.confidence == 0.94
        assert scope.explicit_class_match is True
        assert scope.requires_safety_context is False

    def test_confidence_boundary_constraints(self) -> None:
        """Verify confidence must be between 0.0 and 1.0."""
        # Valid boundaries
        assert QueryScope(confidence=0.0, intent=QueryIntent.GENERAL_KNOWLEDGE).confidence == 0.0
        assert QueryScope(confidence=1.0, intent=QueryIntent.GENERAL_KNOWLEDGE).confidence == 1.0

        # Invalid: < 0.0
        with pytest.raises(ValidationError):
            QueryScope(confidence=-0.1, intent=QueryIntent.GENERAL_KNOWLEDGE)

        # Invalid: > 1.0
        with pytest.raises(ValidationError):
            QueryScope(confidence=1.05, intent=QueryIntent.GENERAL_KNOWLEDGE)

    def test_invalid_domain_rejected(self) -> None:
        """Verify invalid domain strings raise ValidationError."""
        with pytest.raises(ValidationError):
            QueryScope(domain="invalid_domain", confidence=0.8, intent=QueryIntent.GENERAL_KNOWLEDGE)  # type: ignore[arg-type]

    def test_invalid_class_scope_rejected(self) -> None:
        """Verify invalid classifier class strings raise ValidationError."""
        with pytest.raises(ValidationError):
            QueryScope(class_scopes=["fake_cancer_type"], confidence=0.8, intent=QueryIntent.GENERAL_KNOWLEDGE)  # type: ignore[arg-type]

    def test_invalid_intent_rejected(self) -> None:
        """Verify invalid intent strings raise ValidationError."""
        with pytest.raises(ValidationError):
            QueryScope(intent="diagnose_patient", confidence=0.8)  # type: ignore[arg-type]


class TestCanonicalExamples:
    """Tests for canonical examples A through H specified in Phase 3 prompt."""

    def test_example_a_general(self, classifier: QueryScopeClassifier) -> None:
        """Example A: 'What is cancer?' -> general_oncology, general_knowledge."""
        result = classifier.classify("What is cancer?")

        assert result.domain == QueryDomain.GENERAL_ONCOLOGY
        assert result.class_scopes == []
        assert result.class_scope is None
        assert result.intent == QueryIntent.GENERAL_KNOWLEDGE
        assert result.confidence >= 0.90
        assert result.explicit_class_match is False
        assert result.requires_safety_context is False

    def test_example_b_colon_adenocarcinoma(self, classifier: QueryScopeClassifier) -> None:
        """Example B: 'What are the histological features of colon adenocarcinoma?'."""
        result = classifier.classify("What are the histological features of colon adenocarcinoma?")

        assert result.domain == QueryDomain.COLON
        assert result.class_scopes == [ClassScope.COLON_ADENOCARCINOMA]
        assert result.class_scope == ClassScope.COLON_ADENOCARCINOMA
        assert result.intent == QueryIntent.HISTOPATHOLOGY
        assert result.confidence >= 0.95
        assert result.explicit_class_match is True
        assert result.requires_safety_context is False

    def test_example_c_lung_adenocarcinoma(self, classifier: QueryScopeClassifier) -> None:
        """Example C: 'What does lepidic growth mean?' -> lung, lung_adenocarcinoma."""
        result = classifier.classify("What does lepidic growth mean?")

        assert result.domain == QueryDomain.LUNG
        assert result.class_scopes == [ClassScope.LUNG_ADENOCARCINOMA]
        assert result.class_scope == ClassScope.LUNG_ADENOCARCINOMA
        assert result.intent == QueryIntent.HISTOPATHOLOGY
        assert result.confidence >= 0.80
        assert result.explicit_class_match is False
        assert result.requires_safety_context is False

    def test_example_d_lung_comparison(self, classifier: QueryScopeClassifier) -> None:
        """Example D: 'How are lung adenocarcinoma and squamous cell carcinoma different?'."""
        result = classifier.classify("How are lung adenocarcinoma and squamous cell carcinoma different?")

        assert result.domain == QueryDomain.COMPARISON
        assert ClassScope.LUNG_ADENOCARCINOMA in result.class_scopes
        assert ClassScope.LUNG_SQUAMOUS_CELL_CARCINOMA in result.class_scopes
        assert result.intent == QueryIntent.COMPARISON
        assert result.confidence >= 0.95
        assert result.explicit_class_match is True
        assert result.requires_safety_context is False

    def test_example_e_biomarker_limitation(self, classifier: QueryScopeClassifier) -> None:
        """Example E: 'Can H&E prove an EGFR mutation?' -> lung, biomarker, safety_context=True."""
        result = classifier.classify("Can H&E prove an EGFR mutation?")

        assert result.domain == QueryDomain.LUNG
        assert result.class_scopes == []
        assert result.intent == QueryIntent.BIOMARKER
        assert result.confidence >= 0.90
        assert result.explicit_class_match is False
        assert result.requires_safety_context is True

    def test_example_f_staging(self, classifier: QueryScopeClassifier) -> None:
        """Example F: 'Can this histopathology image determine TNM stage?' -> safety_policy, staging."""
        result = classifier.classify("Can this histopathology image determine TNM stage?")

        assert result.domain == QueryDomain.SAFETY_POLICY
        assert result.class_scopes == []
        assert result.intent == QueryIntent.STAGING
        assert result.confidence >= 0.95
        assert result.explicit_class_match is False
        assert result.requires_safety_context is True

    def test_example_g_treatment(self, classifier: QueryScopeClassifier) -> None:
        """Example G: 'What treatment should I take for this cancer?' -> safety_policy, treatment."""
        result = classifier.classify("What treatment should I take for this cancer?")

        assert result.domain == QueryDomain.SAFETY_POLICY
        assert result.class_scopes == []
        assert result.intent == QueryIntent.TREATMENT
        assert result.confidence >= 0.95
        assert result.explicit_class_match is False
        assert result.requires_safety_context is True

    def test_example_h_ambiguous(self, classifier: QueryScopeClassifier) -> None:
        """Example H: 'Tell me about cancer.' -> general_oncology, general_knowledge."""
        result = classifier.classify("Tell me about cancer.")

        assert result.domain == QueryDomain.GENERAL_ONCOLOGY
        assert result.class_scopes == []
        assert result.class_scope is None
        assert result.intent == QueryIntent.GENERAL_KNOWLEDGE
        assert result.confidence >= 0.85
        assert result.explicit_class_match is False
        assert result.requires_safety_context is False


class TestDetailedMedicalRouting:
    """Tests for specialized intents, IHC, and benign tissue questions."""

    def test_ihc_routing(self, classifier: QueryScopeClassifier) -> None:
        """Verify 'What is p40 used for in lung pathology?' maps to lung and immunohistochemistry."""
        result = classifier.classify("What is p40 used for in lung pathology?")

        assert result.domain == QueryDomain.LUNG
        assert result.intent == QueryIntent.IMMUNOHISTOCHEMISTRY
        assert result.requires_safety_context is False

    def test_benign_colonic_tissue_routing(self, classifier: QueryScopeClassifier) -> None:
        """Verify 'What do normal colon crypts look like?' maps to colon and benign_colonic_tissue."""
        result = classifier.classify("What do normal colon crypts look like?")

        assert result.domain == QueryDomain.COLON
        assert result.class_scopes == [ClassScope.BENIGN_COLONIC_TISSUE]
        assert result.intent == QueryIntent.HISTOPATHOLOGY
        assert result.requires_safety_context is False

    def test_benign_lung_tissue_routing(self, classifier: QueryScopeClassifier) -> None:
        """Verify 'What are the features of benign lung tissue?' maps to lung and benign_lung_tissue."""
        result = classifier.classify("What are the features of benign lung tissue?")

        assert result.domain == QueryDomain.LUNG
        assert result.class_scopes == [ClassScope.BENIGN_LUNG_TISSUE]
        assert result.intent == QueryIntent.HISTOPATHOLOGY
        assert result.explicit_class_match is True

    def test_lung_squamous_cell_carcinoma_routing(self, classifier: QueryScopeClassifier) -> None:
        """Verify 'Explain squamous cell carcinoma of the lung.' maps to lung_squamous_cell_carcinoma."""
        result = classifier.classify("Explain squamous cell carcinoma of the lung.")

        assert result.domain == QueryDomain.LUNG
        assert result.class_scopes == [ClassScope.LUNG_SQUAMOUS_CELL_CARCINOMA]
        assert result.explicit_class_match is True
        assert result.intent == QueryIntent.CLASS_EXPLANATION

    def test_benign_label_safety_boundary(self, classifier: QueryScopeClassifier) -> None:
        """Verify 'Does benign lung mean no disease?' triggers safety context."""
        result = classifier.classify("Does benign lung mean no disease?")

        assert result.requires_safety_context is True
        assert result.domain == QueryDomain.LUNG

    def test_empty_or_whitespace_query(self, classifier: QueryScopeClassifier) -> None:
        """Verify empty query returns safe null defaults."""
        result = classifier.classify("   ")

        assert result.domain is None
        assert result.class_scopes == []
        assert result.confidence == 0.0
        assert result.requires_safety_context is False
