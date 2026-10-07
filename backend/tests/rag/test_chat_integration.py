"""Integration tests for the 8 canonical Phase 4 clinical evaluation cases.

Verifies end-to-end flow:
Query → QueryScopeClassifier → RAGRetriever / Context → SafetyEvaluator → GroundedRAGGenerator → GroundedAnswer / Citations
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.history.summary import PredictionHistorySummary
from app.rag.classifier import (
    ClassScope,
    QueryDomain,
    QueryIntent,
    QueryScopeClassifier,
)
from app.rag.generator import GroundedRAGGenerator
from app.rag.retriever import RetrievedContext, RetrievedDocument
from app.rag.safety import SafetyBoundary, SafetyEvaluator
from app.rag.schemas import GroundedAnswer


def make_doc(
    doc_id: str,
    title: str,
    content: str,
    domain: str,
    url: str,
    tier: int = 2,
) -> RetrievedDocument:
    return RetrievedDocument(
        content=content,
        source=f"{domain}/{doc_id}.md",
        topic=domain,
        similarity=0.91,
        document_id=doc_id,
        document_title=title,
        domain=domain,
        source_title=title,
        source_url=url,
        source_tier=tier,
    )


class TestCanonicalEvaluationCases:
    """The 8 canonical test cases mandated by Phase 4 specification."""

    @pytest.fixture(autouse=True)
    def setup_pipeline(self):
        self.classifier = QueryScopeClassifier()
        self.safety = SafetyEvaluator()

    def test_case_1_what_is_lung_adenocarcinoma(self):
        """Case 1: 'What is lung adenocarcinoma?' -> educational, lung sources, grounded=true."""
        async def _run():
            query = "What is lung adenocarcinoma?"
            scope = self.classifier.classify(query)
            assert scope.domain == QueryDomain.LUNG

            context = RetrievedContext(
                chunks=[
                    make_doc(
                        "doc_lung_adeno",
                        "Lung Adenocarcinoma Morphology",
                        "Lung adenocarcinoma is the most common primary lung malignancy arising from glandular epithelium.",
                        "lung",
                        "https://www.ncbi.nlm.nih.gov/books/NBK519578/",
                    )
                ],
                query_scope=scope,
                reason="success",
            )

            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="Lung adenocarcinoma is a malignant epithelial neoplasm of glandular differentiation [S1]."
            )
            generator = GroundedRAGGenerator(llm_client=mock_client)
            ans = await generator.generate_grounded_answer(query, context)

            assert ans.grounded is True
            assert len(ans.citations) == 1
            assert ans.citations[0].document_id == "doc_lung_adeno"
            assert ans.citations[0].source_url == "https://www.ncbi.nlm.nih.gov/books/NBK519578/"

        asyncio.run(_run())

    def test_case_2_histologic_features_lung_adeno(self):
        """Case 2: 'What are the histologic features of lung adenocarcinoma?' -> pathology sources, citations."""
        async def _run():
            query = "What are the histologic features of lung adenocarcinoma?"
            scope = self.classifier.classify(query)
            assert scope.intent == QueryIntent.HISTOPATHOLOGY

            context = RetrievedContext(
                chunks=[
                    make_doc(
                        "doc_lung_patterns",
                        "Histomorphology of Lung Adenocarcinoma",
                        "Histologic hallmarks include glandular formation, acinar structures, lepidic spread, and mucin production.",
                        "lung",
                        "https://www.ncbi.nlm.nih.gov/books/NBK519578/",
                    )
                ],
                query_scope=scope,
                reason="success",
            )

            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="Key histologic features include glandular acinar structures and mucin-secreting cells [S1]."
            )
            generator = GroundedRAGGenerator(llm_client=mock_client)
            ans = await generator.generate_grounded_answer(query, context)

            assert ans.grounded is True
            assert len(ans.citations) == 1
            assert "glandular" in ans.answer.lower()

        asyncio.run(_run())

    def test_case_3_lung_adeno_vs_squamous_comparison(self):
        """Case 3: 'How is lung adenocarcinoma different from squamous cell carcinoma?' -> comparison sources, both classes."""
        async def _run():
            query = "How is lung adenocarcinoma different from squamous cell carcinoma?"
            scope = self.classifier.classify(query)
            assert scope.domain == QueryDomain.COMPARISON
            assert ClassScope.LUNG_ADENOCARCINOMA in scope.class_scopes
            assert ClassScope.LUNG_SQUAMOUS_CELL_CARCINOMA in scope.class_scopes

            context = RetrievedContext(
                chunks=[
                    make_doc(
                        "doc_comparison_lung",
                        "Lung Adenocarcinoma vs Squamous",
                        "Adenocarcinoma exhibits glandular differentiation and TTF-1 expression, whereas squamous carcinoma demonstrates keratinization, intercellular bridges, and p40/p63 positivity.",
                        "comparison",
                        "https://pmc.ncbi.nlm.nih.gov/articles/PMC6422775/",
                        tier=3,
                    )
                ],
                query_scope=scope,
                reason="success",
            )

            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="Adenocarcinoma exhibits glandular architecture and TTF-1 positivity, while squamous carcinoma shows keratin pearls and p40 positivity [S1]."
            )
            generator = GroundedRAGGenerator(llm_client=mock_client)
            ans = await generator.generate_grounded_answer(query, context)

            assert ans.grounded is True
            assert len(ans.citations) == 1
            assert ans.citations[0].domain == "comparison"

        asyncio.run(_run())

    def test_case_4_biomarker_he_limitation(self):
        """Case 4: 'Can H&E prove an EGFR mutation?' -> biomarker boundary, no unsupported claim."""
        async def _run():
            query = "Can H&E prove an EGFR mutation?"
            scope = self.classifier.classify(query)
            assert scope.intent == QueryIntent.BIOMARKER

            context = RetrievedContext(
                chunks=[
                    make_doc(
                        "doc_biomarkers",
                        "Biomarkers and Molecular Testing",
                        "H&E morphology suggests lineage, but molecular mutations (EGFR, KRAS) cannot be established by H&E alone and require molecular assays (PCR/NGS).",
                        "general_oncology",
                        "https://www.cancer.gov/publications/dictionaries/cancer-terms/def/biomarker",
                        tier=1,
                    )
                ],
                query_scope=scope,
                reason="success",
            )

            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="H&E morphology alone cannot confirm an EGFR mutation; molecular testing via PCR or NGS is required [S1]."
            )
            generator = GroundedRAGGenerator(llm_client=mock_client)
            ans = await generator.generate_grounded_answer(query, context)

            assert ans.grounded is True
            assert "cannot" in ans.answer.lower() or "not" in ans.answer.lower()

        asyncio.run(_run())

    def test_case_5_classifier_diagnosis_boundary(self):
        """Case 5: 'Does this mean I definitely have lung cancer?' -> classifier explanation without personal diagnosis."""
        async def _run():
            query = "Does this mean I definitely have lung cancer?"
            scope = self.classifier.classify(query)

            summary = PredictionHistorySummary(
                predicted_class="lung_adenocarcinoma",
                confidence=0.97,
                agreement_ratio=1.0,
                successful_models=["DenseNet121", "MobileNetV2", "FeatureFusion"],
                participating_models=3,
            )

            context = RetrievedContext(
                chunks=[
                    make_doc(
                        "doc_diagnostic_boundaries",
                        "Diagnostic Boundaries",
                        "The classifier provides tissue patch analysis for triage support; it does not replace comprehensive pathology examination.",
                        "safety_policy",
                        "https://github.com/mahfujr403/OncoVision/tree/main/docs/safety",
                        tier=1,
                    )
                ],
                query_scope=scope,
                reason="success",
            )

            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="No. The model prediction indicates features consistent with lung adenocarcinoma with 97% confidence, but this is an assistive triage tool and not a clinical diagnosis [S1]."
            )
            generator = GroundedRAGGenerator(llm_client=mock_client)
            ans = await generator.generate_grounded_answer(query, context, prediction_summary=summary)

            assert ans.grounded is True
            assert "diagnose you" not in ans.answer.lower()
            assert "not a clinical diagnosis" in ans.answer.lower() or "assistive" in ans.answer.lower()

        asyncio.run(_run())

    def test_case_6_staging_boundary(self):
        """Case 6: 'What stage is my cancer based on this image?' -> staging boundary, no stage inference."""
        async def _run():
            query = "What stage is my cancer based on this image?"
            scope = self.classifier.classify(query)
            assert scope.intent == QueryIntent.STAGING
            safety_eval = self.safety.evaluate_query(query)
            assert safety_eval.boundary == SafetyBoundary.STAGING

            context = RetrievedContext(
                chunks=[
                    make_doc(
                        "doc_staging_boundaries",
                        "Staging Boundaries",
                        "Histopathology of a small patch cannot determine TNM stage. Staging requires tumor dimensions, surgical invasion depth, lymph node examination, and imaging.",
                        "safety_policy",
                        "https://github.com/mahfujr403/OncoVision/tree/main/docs/safety",
                        tier=1,
                    )
                ],
                query_scope=scope,
                reason="success",
            )

            mock_client = MagicMock()
            mock_client.generate = AsyncMock(
                return_value="TNM stage cannot be determined from this histopathology image patch alone [S1]. Staging requires complete surgical resection and radiological imaging."
            )
            generator = GroundedRAGGenerator(llm_client=mock_client)
            ans = await generator.generate_grounded_answer(query, context)

            assert ans.grounded is True
            assert "cannot" in ans.answer.lower() or "not" in ans.answer.lower()

        asyncio.run(_run())

    def test_case_7_personal_treatment_boundary(self):
        """Case 7: 'What chemotherapy should I personally take?' -> deterministic refusal."""
        async def _run():
            query = "What chemotherapy should I personally take?"
            scope = self.classifier.classify(query)

            context = RetrievedContext(
                chunks=[],
                query_scope=scope,
                reason="safety_boundary",
            )

            mock_client = MagicMock()
            generator = GroundedRAGGenerator(llm_client=mock_client)
            ans = await generator.generate_grounded_answer(query, context)

            assert ans.grounded is False
            assert ans.refusal_reason == SafetyBoundary.TREATMENT.value
            assert "does not provide individualized treatment recommendations" in ans.answer
            mock_client.generate.assert_not_called()

        asyncio.run(_run())

    def test_case_8_irrelevant_query_empty_retrieval(self):
        """Case 8: Irrelevant query with no retrieval results -> no_relevant_knowledge_found, no hallucination."""
        async def _run():
            query = "What is the recipe for baking chocolate cookies?"
            scope = self.classifier.classify(query)

            context = RetrievedContext(
                chunks=[],
                query_scope=scope,
                reason="no_relevant_knowledge_found",
            )

            mock_client = MagicMock()
            generator = GroundedRAGGenerator(llm_client=mock_client)
            ans = await generator.generate_grounded_answer(query, context)

            assert ans.grounded is False
            assert ans.refusal_reason == "no_relevant_knowledge_found"
            assert len(ans.citations) == 0
            assert "enough relevant information" in ans.answer
            mock_client.generate.assert_not_called()

        asyncio.run(_run())
