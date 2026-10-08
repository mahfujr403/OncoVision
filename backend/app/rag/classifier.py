"""Query Scope Classification for OncoVision RAG (Phase 3).

Provides deterministic, typed intent and domain routing across medical domains,
classifier class scopes, and safety boundary conditions.
"""

from __future__ import annotations

import logging
import re
from enum import Enum

from pydantic import BaseModel, Field

from app.rag.provenance import is_explicit_developer_query

logger = logging.getLogger(__name__)


class QueryDomain(str, Enum):
    """Canonical medical knowledge base domains."""

    GENERAL_ONCOLOGY = "general_oncology"
    HISTOPATHOLOGY = "histopathology"
    COLON = "colon"
    LUNG = "lung"
    COMPARISON = "comparison"
    CLINICAL_EXPLANATION = "clinical_explanation"
    CLASSIFIER_CONTEXT = "classifier_context"
    SAFETY_POLICY = "safety_policy"
    DEVELOPER_INFO = "developer_info"
    PLATFORM_INFO = "platform_info"


class ClassScope(str, Enum):
    """The five canonical LC25000 histopathology classifier classes."""

    COLON_ADENOCARCINOMA = "colon_adenocarcinoma"
    BENIGN_COLONIC_TISSUE = "benign_colonic_tissue"
    LUNG_ADENOCARCINOMA = "lung_adenocarcinoma"
    BENIGN_LUNG_TISSUE = "benign_lung_tissue"
    LUNG_SQUAMOUS_CELL_CARCINOMA = "lung_squamous_cell_carcinoma"


class QueryIntent(str, Enum):
    """Deterministic retrieval intent classifications."""

    GENERAL_KNOWLEDGE = "general_knowledge"
    HISTOPATHOLOGY = "histopathology"
    CLASS_EXPLANATION = "class_explanation"
    COMPARISON = "comparison"
    BIOMARKER = "biomarker"
    IMMUNOHISTOCHEMISTRY = "immunohistochemistry"
    STAGING = "staging"
    TREATMENT = "treatment"
    CLASSIFIER_EXPLANATION = "classifier_explanation"
    SAFETY_BOUNDARY = "safety_boundary"
    CONVERSATIONAL = "conversational"


class QueryScope(BaseModel):
    """Strict typed output schema for query scope detection."""

    domain: QueryDomain | None = None
    class_scopes: list[ClassScope] = Field(default_factory=list)
    intent: QueryIntent = QueryIntent.GENERAL_KNOWLEDGE
    confidence: float = Field(ge=0.0, le=1.0)
    explicit_class_match: bool = False
    requires_safety_context: bool = False

    @property
    def class_scope(self) -> ClassScope | None:
        """Helper returning the primary class scope, or None."""
        return self.class_scopes[0] if self.class_scopes else None


class QueryScopeClassifier:
    """Lightweight deterministic classifier for retrieval query routing.
    
    Adheres to conservative medical routing principles: never forces an ambiguous
    query into a narrow class scope.
    """

    def classify(self, query: str) -> QueryScope:
        """Classify a user query into a strictly typed QueryScope."""
        if not query or not query.strip():
            return QueryScope(
                domain=None,
                class_scopes=[],
                intent=QueryIntent.GENERAL_KNOWLEDGE,
                confidence=0.0,
                explicit_class_match=False,
                requires_safety_context=False,
            )

        norm_query = query.strip().lower().replace("’", "'").replace("‘", "'")

        # 1. Safety Context Detection
        requires_safety = self._detect_safety_context(norm_query)

        # 2. Intent Detection
        intent = self._detect_intent(norm_query, requires_safety)

        # 3. Class Scope Detection
        class_scopes, explicit_match = self._detect_class_scopes(norm_query)

        # 4. Domain Detection
        domain = self._detect_domain(norm_query, intent, class_scopes, requires_safety)

        # 5. Confidence Calculation
        confidence = self._calculate_confidence(
            norm_query=norm_query,
            domain=domain,
            class_scopes=class_scopes,
            intent=intent,
            explicit_match=explicit_match,
            requires_safety=requires_safety,
        )

        return QueryScope(
            domain=domain,
            class_scopes=class_scopes,
            intent=intent,
            confidence=confidence,
            explicit_class_match=explicit_match,
            requires_safety_context=requires_safety,
        )

    def _detect_safety_context(self, q: str) -> bool:
        """Identify questions requiring clinical boundary and safety policy awareness."""
        safety_patterns = [
            # Diagnosing or proving disease from an image
            r"\b(prove|proves|proving|confirm|guarantee)\b.*\b(cancer|tumor|malignan|disease)\b",
            # Image-based staging or TNM inference
            r"\b(can|could|will)\b.*\b(image|slide|h&e|he|biopsy)\b.*\b(tell|determine|give|show|assign)\b.*\b(stage|staging|tnm)\b",
            r"\b(determine|tell|know|assign)\b.*\b(stage|staging|tnm)\b.*\b(image|slide)\b",
            r"\bcan this (image|histopathology image|slide) determine (tnm )?stage\b",
            # Molecular mutation proof from H&E alone
            r"\b(can|could)\b.*\b(h&e|h and e|histology|image)\b.*\b(prove|confirm|detect)\b.*\b(egfr|alk|kras|braf|mutation)\b",
            r"\b(prove|detect|confirm)\b.*\b(egfr|alk|kras|braf|mutation)\b.*\b(from|using|with)\b.*\b(h&e|image)\b",
            r"\bcan h&e prove an? (egfr|kras|alk|braf|mutation)\b",
            r"\b(tell|know|infer|determine|detect)\b.*\b(egfr|alk|kras|braf|mutation)\b.*\b(from|with|using)\b.*\b(image|slide|h&e)\b",
            r"\bwhy can'?t you\b.*\b(tell|detect|infer|know)\b.*\b(egfr|alk|kras|mutation)\b",
            # Personal treatment advice
            r"\bwhat treatment should i (take|have|use|get)\b",
            r"\bhow should i treat (my|this) (cancer|tumor)\b",
            r"\bprescribe\b",
            # Benign label vs absence of disease
            r"\bdoes benign\b.*\bmean no disease\b",
            # Patient personal diagnosis
            r"\bdo i have cancer\b",
            r"\bdiagnose my (symptom|pain|condition)\b",
        ]
        return any(re.search(pat, q) for pat in safety_patterns)

    def _detect_intent(self, q: str, requires_safety: bool) -> QueryIntent:
        """Classify retrieval question intent."""
        # Conversational greetings & assistant identity
        conversational_patterns = [
            r"^(hi|hello|hey|greetings|good (morning|afternoon|evening))\b",
            r"^(who are you|what can you do|how can you help|tell me about yourself|help me|what are you)\b",
            r"^(কে আপনি|আপনি কে|হ্যালো|হাই|নমস্কার|কেমন আছেন)\b",
        ]
        if any(re.search(pat, q) for pat in conversational_patterns):
            has_clinical_keywords = any(kw in q for kw in [
                "cancer", "tumor", "lung", "colon", "adenocarcinoma", "squamous", "tissue", "biopsy", "ihc", "mutation",
                "ক্যান্সার", "ফুসফুস", "কোলন", "হিস্টোপ্যাথলজি"
            ])
            if not has_clinical_keywords:
                return QueryIntent.CONVERSATIONAL

        # Comparison patterns
        if any(
            re.search(pat, q)
            for pat in [
                r"\b(difference between|different from|differ from|differ\b|versus|vs\.?|compare|distinguish between)\b",
                r"\bhow (do|are|is)\b.*\b(different|differ)\b",
                r"\b(পার্থক্য|তুলনা)\b",
            ]
        ):
            return QueryIntent.COMPARISON

        # Staging concept or boundary
        if re.search(r"\b(stage|staging|tnm|t[0-4]|n[0-3]|m[0-1])\b", q):
            return QueryIntent.STAGING

        # Treatment concept or boundary
        if re.search(
            r"\b(treatment|therapy|chemotherapy|immunotherapy|resection|surgical|surgery|prescribe|drug|medication)\b",
            q,
        ):
            return QueryIntent.TREATMENT

        # Biomarker / molecular
        if re.search(
            r"\b(egfr|alk|kras|braf|ros1|pdl1|pd-l1|her2|msi|mutation|molecular biomarker|molecular testing)\b",
            q,
        ):
            return QueryIntent.BIOMARKER

        # Immunohistochemistry
        if re.search(
            r"\b(p40|ck7|ck20|ttf-1|ttf1|napsin|ihc|immunohistochemistry|staining pattern)\b",
            q,
        ):
            return QueryIntent.IMMUNOHISTOCHEMISTRY

        # Classifier explanation
        if re.search(
            r"\b(classifier|model output|confidence score|agreement ratio|ai model|prediction score)\b",
            q,
        ):
            return QueryIntent.CLASSIFIER_EXPLANATION

        # Histopathology morphology
        if any(
            re.search(pat, q)
            for pat in [
                r"\b(histology|histological|histopathology|morphology|microscopic|crypts?|lepidic|cribriform|budding|acinar|papillary|intercellular bridges|keratin pearl)\b",
                r"\b(h&e|hematoxylin|eosin|biopsy|cellular|features?|characteristics?)\b",
                r"\b(হিস্টোপ্যাথলজি|হিস্টোপ্যাথলজিক্যাল|বায়োপসি|টিস্যু|লক্ষণ)\b",
            ]
        ):
            return QueryIntent.HISTOPATHOLOGY

        # Class explanation (e.g. "what is lung adenocarcinoma", "explain squamous cell carcinoma", Bengali explanations)
        if re.search(r"^(what is|what are|explain|describe|tell me about)\b", q) or re.search(r"\b(লক্ষণ কি|লক্ষণ কী|চিহ্ন|কী|কি|ব্যাখ্যা)\b", q):
            if any(kw in q for kw in ["squamous", "adenocarcinoma", "carcinoma", "benign", "colon", "lung", "tissue", "ক্যান্সার", "কোলন", "ফুসফুস", "টিস্যু"]):
                return QueryIntent.CLASS_EXPLANATION

        # Developer and platform inquiries
        if is_explicit_developer_query(q):
            return QueryIntent.CLASSIFIER_EXPLANATION
        if any(w in q for w in ["what is oncovision", "about oncovision", "how does oncovision work", "oncovision features"]):
            return QueryIntent.CLASSIFIER_EXPLANATION

        # General safety boundary
        if requires_safety:
            return QueryIntent.SAFETY_BOUNDARY

        return QueryIntent.GENERAL_KNOWLEDGE

    def _detect_class_scopes(self, q: str) -> tuple[list[ClassScope], bool]:
        """Map canonical classifier classes and detect explicit naming."""
        matched: list[ClassScope] = []
        explicit = False

        # 1. Colon adenocarcinoma
        if re.search(
            r"\b(colon adenocarcinoma|colorectal adenocarcinoma|adenocarcinoma of the colon|colon adeno|colonic adenocarcinoma)\b",
            q,
        ):
            matched.append(ClassScope.COLON_ADENOCARCINOMA)
            explicit = True
        elif "tumor budding" in q and "lung" not in q:
            matched.append(ClassScope.COLON_ADENOCARCINOMA)

        # 2. Benign colonic tissue
        if re.search(
            r"\b(benign colonic tissue|benign colon|benign colonic|normal colon|normal colonic)\b",
            q,
        ):
            matched.append(ClassScope.BENIGN_COLONIC_TISSUE)
            explicit = True
        elif re.search(r"\b(colon crypts?|colonic crypts?|hyperplastic polyp)\b", q):
            matched.append(ClassScope.BENIGN_COLONIC_TISSUE)

        # 3. Lung adenocarcinoma
        if re.search(
            r"\b(lung adenocarcinoma|adenocarcinoma of the lung|lung adeno)\b",
            q,
        ):
            matched.append(ClassScope.LUNG_ADENOCARCINOMA)
            explicit = True
        elif "lepidic" in q:
            matched.append(ClassScope.LUNG_ADENOCARCINOMA)

        # 4. Benign lung tissue
        if re.search(
            r"\b(benign lung tissue|benign lung|normal lung|normal pulmonary|benign pulmonary)\b",
            q,
        ):
            matched.append(ClassScope.BENIGN_LUNG_TISSUE)
            explicit = True

        # 5. Lung squamous cell carcinoma
        if re.search(
            r"\b(lung squamous cell carcinoma|squamous cell carcinoma of the lung|lung squamous|lung scc|squamous cell lung)\b",
            q,
        ):
            matched.append(ClassScope.LUNG_SQUAMOUS_CELL_CARCINOMA)
            explicit = True
        elif re.search(r"\bsquamous cell carcinoma\b", q) and "colon" not in q:
            matched.append(ClassScope.LUNG_SQUAMOUS_CELL_CARCINOMA)
            explicit = True

        return matched, explicit

    def _detect_domain(
        self,
        q: str,
        intent: QueryIntent,
        class_scopes: list[ClassScope],
        requires_safety: bool,
    ) -> QueryDomain | None:
        """Determine target medical knowledge domain."""
        # Safety policy domain: strictly when asking about image staging, image prescription, or diagnostic boundaries
        if requires_safety and intent in {QueryIntent.STAGING, QueryIntent.TREATMENT, QueryIntent.SAFETY_BOUNDARY}:
            if re.search(r"\b(stage|staging|tnm)\b", q) or re.search(r"\b(treatment|treat|prescribe)\b", q):
                return QueryDomain.SAFETY_POLICY

        # Comparison domain
        if intent == QueryIntent.COMPARISON or len(class_scopes) > 1:
            return QueryDomain.COMPARISON

        # Class scope driven domain
        if any(
            cs in {ClassScope.COLON_ADENOCARCINOMA, ClassScope.BENIGN_COLONIC_TISSUE}
            for cs in class_scopes
        ):
            return QueryDomain.COLON
        if any(
            cs in {ClassScope.LUNG_ADENOCARCINOMA, ClassScope.BENIGN_LUNG_TISSUE, ClassScope.LUNG_SQUAMOUS_CELL_CARCINOMA}
            for cs in class_scopes
        ):
            return QueryDomain.LUNG

        # Organ keywords (including Bengali)
        has_colon = any(w in q for w in ["colon", "colorectal", "bowel", "rectum", "rectal", "কোলন", "কলোরেক্টাল", "মলাশয়", "বৃহদন্ত্র"])
        has_lung = any(w in q for w in ["lung", "pulmonary", "bronchial", "pleural", "egfr", "p40", "ttf-1", "napsin", "ফুসফুস", "পালমোনারি", "শ্বাসনালী"])
        if has_colon and has_lung:
            return QueryDomain.COMPARISON
        if has_colon:
            return QueryDomain.COLON
        if has_lung:
            return QueryDomain.LUNG

        # General histopathology (no specific organ)
        if intent == QueryIntent.HISTOPATHOLOGY or any(
            w in q for w in ["histopathology", "biopsy", "h&e", "staining", "pathology", "হিস্টোপ্যাথলজি", "হিস্টোপ্যাথলজিক্যাল", "বায়োপসি", "টিস্যু"]
        ):
            return QueryDomain.HISTOPATHOLOGY

        # Developer and platform inquiries
        if is_explicit_developer_query(q):
            return QueryDomain.DEVELOPER_INFO
        if any(w in q for w in ["what is oncovision", "about oncovision", "how does oncovision work", "oncovision features", "who built", "system architecture"]):
            return QueryDomain.PLATFORM_INFO

        # General oncology (e.g. "what is cancer", "tumor basics")
        if any(w in q for w in ["cancer", "tumor", "oncology", "neoplasm", "carcinoma", "malignan", "ক্যান্সার", "ক্যানসার", "টিউমার"]):
            return QueryDomain.GENERAL_ONCOLOGY

        return None

    def _calculate_confidence(
        self,
        norm_query: str,
        domain: QueryDomain | None,
        class_scopes: list[ClassScope],
        intent: QueryIntent,
        explicit_match: bool,
        requires_safety: bool,
    ) -> float:
        """Calculate explainable classification confidence score between 0.0 and 1.0."""
        if intent == QueryIntent.CONVERSATIONAL:
            return 0.99
        if is_explicit_developer_query(norm_query):
            return 0.98
        if domain in {QueryDomain.DEVELOPER_INFO, QueryDomain.PLATFORM_INFO}:
            return 0.98
        if explicit_match and domain is not None:
            return 0.97
        if domain == QueryDomain.COMPARISON:
            return 0.98
        if requires_safety and domain == QueryDomain.SAFETY_POLICY:
            return 0.97
        if requires_safety:
            return 0.96
        if explicit_match:
            return 0.94
        if domain in {QueryDomain.COLON, QueryDomain.LUNG}:
            return 0.85
        if domain == QueryDomain.GENERAL_ONCOLOGY:
            return 0.95 if "what is cancer" in norm_query else 0.90
        if domain is not None:
            return 0.80
        return 0.50
