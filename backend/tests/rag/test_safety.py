"""Unit and boundary tests for SafetyEvaluator (Phase 4).

Tests deterministic clinical safety enforcement, boundary classification,
refusal rules, and post-generation safety verification.
"""

from __future__ import annotations

import pytest

from app.rag.safety import (
    BIOMARKER_BOUNDARY_GUIDANCE,
    DIAGNOSIS_REFUSAL_MESSAGE,
    STAGING_BOUNDARY_GUIDANCE,
    TREATMENT_REFUSAL_MESSAGE,
    SafetyBoundary,
    SafetyEvaluator,
)


@pytest.fixture
def evaluator() -> SafetyEvaluator:
    return SafetyEvaluator()


class TestDiagnosisBoundary:
    """Test personal medical diagnosis boundary checks."""

    def test_direct_cancer_diagnosis_refused(self, evaluator: SafetyEvaluator):
        queries = [
            "Do I have cancer?",
            "Could I have cancer?",
            "Tell me if I have cancer",
            "Diagnose me",
            "What cancer do I have based on my symptoms?",
        ]
        for q in queries:
            eval_res = evaluator.evaluate_query(q, has_prediction=False)
            assert eval_res.boundary == SafetyBoundary.DIAGNOSIS, f"Failed for {q}"
            assert eval_res.requires_deterministic_refusal is True
            assert eval_res.refusal_message == DIAGNOSIS_REFUSAL_MESSAGE

    def test_symptom_triage_refused(self, evaluator: SafetyEvaluator):
        q = "I have blood in my stool and severe abdominal pain, what cancer is this?"
        eval_res = evaluator.evaluate_query(q, has_prediction=False)
        assert eval_res.boundary == SafetyBoundary.DIAGNOSIS
        assert eval_res.requires_deterministic_refusal is True
        assert "cannot provide personal medical diagnoses" in eval_res.refusal_message

    def test_prediction_explanation_does_not_refuse_educational_context(
        self, evaluator: SafetyEvaluator
    ):
        q = "Does this mean I definitely have lung cancer?"
        eval_res = evaluator.evaluate_query(q, has_prediction=True)
        assert eval_res.boundary == SafetyBoundary.DIAGNOSIS
        # When prediction context is attached, we explain the boundary rather than flat refusal
        assert eval_res.requires_deterministic_refusal is False
        assert eval_res.boundary_guidance is not None
        assert "not a definitive clinical diagnosis" in eval_res.boundary_guidance


class TestTreatmentBoundary:
    """Test personal treatment and medication prescription boundaries."""

    def test_chemotherapy_prescription_refused(self, evaluator: SafetyEvaluator):
        queries = [
            "What chemotherapy should I take?",
            "What chemotherapy should I personally take?",
            "Which drug should I use?",
            "What medication should I personally take?",
            "Prescribe me something for this tumor",
            "What dosage of cisplatin should I take?",
        ]
        for q in queries:
            eval_res = evaluator.evaluate_query(q)
            assert eval_res.boundary == SafetyBoundary.TREATMENT, f"Failed for {q}"
            assert eval_res.requires_deterministic_refusal is True
            assert eval_res.refusal_message == TREATMENT_REFUSAL_MESSAGE

    def test_general_educational_treatment_not_refused(
        self, evaluator: SafetyEvaluator
    ):
        q = "What are the common general concepts in cancer treatment?"
        eval_res = evaluator.evaluate_query(q)
        assert eval_res.requires_deterministic_refusal is False


class TestStagingBoundary:
    """Test histopathology TNM staging boundaries."""

    def test_staging_from_image_triggers_boundary(self, evaluator: SafetyEvaluator):
        queries = [
            "What stage is my cancer based on this image?",
            "Can you determine the TNM stage from this image?",
            "Can this image determine TNM stage?",
            "What is the TNM stage from this image?",
        ]
        for q in queries:
            eval_res = evaluator.evaluate_query(q)
            assert eval_res.boundary == SafetyBoundary.STAGING, f"Failed for {q}"
            assert eval_res.requires_deterministic_refusal is False
            assert "cannot determine clinical or pathological TNM stage" in eval_res.boundary_guidance


class TestBiomarkerBoundary:
    """Test H&E molecular biomarker boundaries."""

    def test_biomarker_from_he_triggers_guidance(self, evaluator: SafetyEvaluator):
        queries = [
            "Can H&E prove an EGFR mutation?",
            "Can this image confirm KRAS mutation?",
            "Does H&E prove molecular mutations?",
        ]
        for q in queries:
            eval_res = evaluator.evaluate_query(q)
            assert eval_res.boundary == SafetyBoundary.BIOMARKER, f"Failed for {q}"
            assert "cannot confirm or prove molecular mutations" in eval_res.boundary_guidance


class TestClassifierBoundary:
    """Test classifier explanation boundaries."""

    def test_classifier_explanation_query(self, evaluator: SafetyEvaluator):
        q = "Why did the model predict lung adenocarcinoma?"
        eval_res = evaluator.evaluate_query(q)
        assert eval_res.boundary == SafetyBoundary.CLASSIFIER
        assert "automated histopathological image feature extraction" in eval_res.boundary_guidance


class TestPostGenerationValidation:
    """Test answer text validation for prohibited clinical claims."""

    def test_valid_educational_answer_passes(self, evaluator: SafetyEvaluator):
        text = "Lung adenocarcinoma commonly presents with glandular architectures [S1]."
        is_safe, error = evaluator.validate_answer(text)
        assert is_safe is True
        assert error is None

    def test_direct_diagnosis_rejected(self, evaluator: SafetyEvaluator):
        bad_texts = [
            "Based on this slide, I diagnose you with colon adenocarcinoma.",
            "You definitely have cancer.",
            "You have stage IV carcinoma.",
        ]
        for text in bad_texts:
            is_safe, error = evaluator.validate_answer(text)
            assert is_safe is False
            assert "forbidden" in error

    def test_direct_prescription_rejected(self, evaluator: SafetyEvaluator):
        text = "You should start taking 50mg of chemotherapy."
        is_safe, error = evaluator.validate_answer(text)
        assert is_safe is False
        assert "forbidden" in error

    def test_false_biomarker_claim_rejected(self, evaluator: SafetyEvaluator):
        text = "This H&E image confirms the EGFR mutation in the specimen."
        is_safe, error = evaluator.validate_answer(text, boundary=SafetyBoundary.BIOMARKER)
        assert is_safe is False
        assert "biomarker" in error
