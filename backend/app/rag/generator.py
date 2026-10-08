"""Grounded RAG generation service and citation orchestrator (Phase 4).

Coordinates:
- Query scope & context ingestion
- Pre-generation safety evaluation & deterministic boundary enforcement
- Numbered citation prompt assembly ([S1], [S2]...)
- Async Gemini generation with timeout & retry handling
- Deterministic citation extraction & provenance mapping
- Unsupported citation stripping & grounding validation
- Structured telemetry logging (never exposing secrets or PHI)
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from app.core.settings import get_settings
from app.history.summary import PredictionHistorySummary
from app.llm.client import GeminiClient, get_gemini_client
from app.rag.grounding import GroundingDecision, GroundingEvaluator
from app.rag.observability import (
    EVENT_CITATION_VALIDATION,
    EVENT_GENERATION_COMPLETED,
    EVENT_GENERATION_FAILED,
    EVENT_GENERATION_STARTED,
    EVENT_GENERATION_TIMEOUT,
    EVENT_GROUNDING_ACCEPTED,
    EVENT_GROUNDING_REJECTED,
    EVENT_SAFETY_REFUSAL,
    RAGErrorCategory,
    RAGTelemetryContext,
)
from app.rag.prompts import (
    GROUNDED_RAG_SYSTEM_PROMPT,
    build_grounded_user_prompt,
    format_grounded_context_sources,
)
from app.rag.provenance import is_explicit_developer_query, is_meta_source_query
from app.rag.retriever import RetrievedContext, RetrievedDocument
from app.rag.safety import (
    BIOMARKER_BOUNDARY_GUIDANCE,
    DEVELOPER_ATTRIBUTION_REFUSAL_MESSAGE,
    DIAGNOSIS_REFUSAL_MESSAGE,
    PREDICTION_CONFLICT_MESSAGE,
    STAGING_BOUNDARY_GUIDANCE,
    TREATMENT_REFUSAL_MESSAGE,
    VISUAL_EVIDENCE_REFUSAL_MESSAGE,
    SafetyBoundary,
    SafetyEvaluator,
)
from app.rag.schemas import Citation, GroundedAnswer

logger = logging.getLogger(__name__)

# Stopwords and reporting terms excluded from claim-evidence lexical matching
GENERIC_AND_MEDICAL_STOPWORDS: set[str] = {
    # Standard English stopwords
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "s", "t", "d", "ll", "m", "re", "ve",
    # Reporting verbs and discourse adverbs
    "also", "generally", "commonly", "often", "frequently", "typically", "usually",
    "primarily", "mainly", "specifically", "especially", "largely", "rarely",
    "exhibits", "presents", "shows", "demonstrates", "include", "includes", "including",
    "states", "describes", "defines", "defined", "characterized", "identifies", "identified",
    "according", "per", "based", "found", "seen", "noted", "reported", "associated",
    "indicates", "supports", "suggests", "considered", "known", "well", "may",
    "might", "must", "can", "will", "could", "would", "shall", "yes", "no",
    # Generic medical terminology that provides zero discriminative evidence
    "patient", "patients", "cancer", "cancers", "tumor", "tumors", "tumour", "tumours",
    "neoplasm", "neoplasms", "malignancy", "malignancies", "treatment", "treatments",
    "therapy", "therapies", "disease", "diseases", "clinical", "clinically", "health",
    "condition", "conditions", "study", "studies", "common", "generic", "medical",
    "terminology", "cell", "cells", "cellular", "tissue", "tissues", "finding",
    "findings", "result", "results", "report", "reports", "case", "cases",
    "type", "types", "care", "doctor", "doctors", "medicine", "medicines",
    "physician", "physicians", "pathologist", "pathologists", "sample", "samples",
    "specimen", "specimens", "biopsy", "biopsies", "feature", "features",
    "evidence", "context", "information", "data", "source", "sources", "lineage",
    "growth", "grow", "grows", "growing",
    "verify", "verifies", "verified", "verifying",
    "detail", "details", "refer", "refers", "reference", "references",
    "model", "models", "prediction", "predictions", "confidence", "consistent",
    "tool", "tools", "assistive", "assist", "diagnosis", "diagnoses", "diagnostic", "diagnostics",
}

# Institutional attribution patterns to check against retrieved documents
INSTITUTIONAL_ATTRIBUTION_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bWHO\b"), "World Health Organization (WHO)"),
    (re.compile(r"\bWorld\s+Health\s+Organization\b", re.IGNORECASE), "World Health Organization"),
    (re.compile(r"\b(?:NCI\s+guidelines?|National\s+Cancer\s+Institute\s+guidelines?)\b", re.IGNORECASE), "NCI guidelines"),
    (re.compile(r"\b(?:NCI|National\s+Cancer\s+Institute)\b"), "National Cancer Institute (NCI)"),
    (re.compile(r"\bCDC\b"), "CDC"),
    (re.compile(r"\bCenters\s+for\s+Disease\s+Control\b", re.IGNORECASE), "Centers for Disease Control"),
    (re.compile(r"\bFDA\b"), "FDA"),
    (re.compile(r"\bFood\s+and\s+Drug\s+Administration\b", re.IGNORECASE), "Food and Drug Administration"),
    (re.compile(r"\bNCCN\b"), "NCCN"),
    (re.compile(r"\bNational\s+Comprehensive\s+Cancer\s+Network\b", re.IGNORECASE), "NCCN"),
    (re.compile(r"\bASCO\b"), "ASCO"),
    (re.compile(r"\bAmerican\s+Society\s+of\s+Clinical\s+Oncology\b", re.IGNORECASE), "ASCO"),
    (re.compile(r"\b(?:clinical\s+guidelines?|oncology\s+guidelines?|practice\s+guidelines?|per\s+guidelines|according\s+to\s+guidelines|guidelines\s+state|guidelines\s+recommend)\b", re.IGNORECASE), "clinical guidelines"),
]

# Developer attribution patterns (strictly prohibited as medical sources)
DEVELOPER_ATTRIBUTION_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:according\s+to|per|based\s+on|from|in|as\s+stated\s+by)\s+(?:the\s+)?(?:developer|author|mahfujur|mahfuj)'?s?\s+(?:github|google\s+scholar|portfolio|website|repo|profile)\b", re.IGNORECASE), "developer repository/profile"),
    (re.compile(r"\b(?:developer|author|mahfujur|mahfuj)'?s?\s+(?:github|google\s+scholar|portfolio|website|repo)\s+(?:states|shows|confirms|reports|describes|indicates|supports|proves|notes)\b", re.IGNORECASE), "developer repository/profile"),
    (re.compile(r"\b(?:according\s+to|per|as\s+stated\s+by)\s+(?:the\s+)?(?:developer|author|md\.?\s*mahfujur\s+rahman|mahfujur\s+rahman)\b", re.IGNORECASE), "developer personal attribution"),
    (re.compile(r"\b(?:grounded\s+in|sourced\s+from|derived\s+from|attributed\s+to)\s+(?:the\s+)?(?:developer|author|mahfujur|mahfuj)'?s?\s+(?:github|google\s+scholar|portfolio|repo)\b", re.IGNORECASE), "developer repository/profile"),
]

# Unrequested developer / portfolio promotional boilerplate patterns
DEVELOPER_PROMOTIONAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(?:contact|reach\s+out\s+to|email)\s+(?:the\s+)?(?:developer|author|creator|me)\b", re.IGNORECASE),
    re.compile(r"\b(?:for\s+inquiries|for\s+questions|for\s+collaboration|for\s+more\s+information),?\s+(?:contact|visit|reach|email|see)\b", re.IGNORECASE),
    re.compile(r"\bmahfujr403(?:@gmail\.com)?\b", re.IGNORECASE),
    re.compile(r"\b\+8801771431724\b"),
    re.compile(r"\b(?:visit|check\s+out|view|see)\s+(?:the|my)?\s*(?:developer'?s?|author'?s?)?\s*(?:portfolio|github|google\s+scholar|repo|linkedin)\b", re.IGNORECASE),
    re.compile(r"\b(?:developer|author|creator)'?s?\s+(?:portfolio|github|google\s+scholar|profile|linkedin|website)\b", re.IGNORECASE),
    re.compile(r"\b(?:google\s+scholar\s+profile|github\s+profile|portfolio\s+website)\b", re.IGNORECASE),
    re.compile(r"\b(?:developed|created|authored|designed|built)\s+by\s+(?:md\.?\s*mahfujur\s+rahman|mahfujur\s+rahman|mahfuj)\b", re.IGNORECASE),
    re.compile(r"\b(?:creator|lead\s+developer|lead\s+author|author|developer)\s*(?::|-)\s*(?:md\.?\s*mahfujur\s+rahman|mahfujur\s+rahman)\b", re.IGNORECASE),
    re.compile(r"\bmd\.?\s*mahfujur\s+rahman\b", re.IGNORECASE),
    re.compile(r"\b(?:oncovision\s+ai\s+was\s+(?:designed|architected|developed|created)\s+by)\b", re.IGNORECASE),
    re.compile(r"\b(?:for\s+more\s+(?:information|details|code),?\s+(?:visit|see|check|go\s+to))\b", re.IGNORECASE),
]

DEVELOPER_URL_PATTERNS: list[re.Pattern] = [
    re.compile(r"https?://(?:www\.)?github\.com/mahfujr403[^\s)\]]*", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?md-mahfujur-rahman\.vercel\.app[^\s)\]]*", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?linkedin\.com/in/mahfujr403[^\s)\]]*", re.IGNORECASE),
    re.compile(r"https?://scholar\.google\.com/citations[^\s)\]]*", re.IGNORECASE),
]

AUTHORITATIVE_MEDICAL_DOMAINS: tuple[str, ...] = (
    "ncbi.nlm.nih.gov",
    "cancer.gov",
    "cap.org",
    "nih.gov",
    "who.int",
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "doi.org",
    "openstax.org",
    "sciencedirect.com",
    "springer.com",
    "nejm.org",
    "thelancet.com",
    "jamanetwork.com",
    "nature.com",
    "bmj.com",
    "ascopubs.org",
    "nccn.org",
    "cdc.gov",
    "fda.gov",
)


def is_developer_boilerplate_unit(unit: str) -> bool:
    """Check if a text unit contains unrequested developer promotional or contact boilerplate."""
    lower = unit.lower()
    # Always preserve explicit negative disclaimers (e.g. "is not from the developer's GitHub")
    if re.search(
        r"\b(?:not|never|neither|no|cannot|without|does\s+not)\b.{1,50}\b(?:developer|github|google\s+scholar|portfolio)\b",
        lower,
    ):
        return False
    # Check developer URL patterns
    for url_pat in DEVELOPER_URL_PATTERNS:
        if url_pat.search(unit):
            return True
    # Check promotional text patterns
    for promo_pat in DEVELOPER_PROMOTIONAL_PATTERNS:
        if promo_pat.search(unit):
            return True
    return False


def is_medical_source_url(url: str, source_map: dict[str, RetrievedDocument]) -> bool:
    """Check if a URL belongs to a retrieved medical document or an authoritative medical domain."""
    clean_url = url.strip().rstrip(".,;!?:)]").lower()
    for doc in source_map.values():
        if doc.source_url and clean_url.rstrip("/") in doc.source_url.lower().rstrip("/"):
            return True
        if doc.source_url and doc.source_url.lower().rstrip("/") in clean_url:
            return True
    for domain in AUTHORITATIVE_MEDICAL_DOMAINS:
        if domain in clean_url:
            return True
    return False

META_REFERENCE_TERMS: set[str] = {
    "see", "refer", "refers", "reference", "references", "info", "information",
    "details", "detail", "more", "source", "sources", "grounded", "support",
    "supports", "supporting", "literature", "retrieved", "referenced", "paper",
    "papers", "derived", "cited", "citing", "overview", "provenance",
}

DISCOURSE_META_TERMS: set[str] = {
    "discussed", "above", "knowledge", "explanation", "following", "summary",
    "outlined", "provided", "support", "supports", "supporting", "listed",
    "question", "answer", "query", "literature", "source", "sources", "grounded",
    "provenance", "derived", "cited", "overview", "documents", "evidence",
    "retrieved", "referenced", "context", "findings", "statements", "material",
}


def extract_salient_terms(text: str) -> set[str]:
    """Extract lowercased salient content terms excluding stopwords and numbers."""
    clean = re.sub(r"\[[^\]]+\]", " ", text)
    clean = re.sub(r"https?://[^\s)\]]+", " ", clean)
    tokens = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", clean.lower())
    return {t for t in tokens if t not in GENERIC_AND_MEDICAL_STOPWORDS and not t.isdigit()}


def check_institutional_attribution(
    sentence: str, docs: list[RetrievedDocument]
) -> tuple[bool, str | None]:
    """Verify that any organizational attribution in the sentence is explicitly grounded in cited docs
    and that no medical facts are attributed to developer metadata."""
    # 1. Developer attribution check (absolute prohibition for medical claims)
    for dev_pattern, dev_name in DEVELOPER_ATTRIBUTION_RULES:
        if dev_pattern.search(sentence):
            # Allow explicit negative disclaimers (e.g. "is not from the developer's GitHub")
            if not re.search(r"\b(?:not|never|neither|no|cannot|without)\b.{1,40}\b(?:developer|github|google\s+scholar)\b", sentence, re.IGNORECASE):
                return False, f"forbidden medical attribution to developer metadata '{dev_name}'"

    # 2. Institutional attribution check against cited documents
    combined_doc_text = " ".join([
        f"{d.content} {d.document_title or ''} {d.source_title or ''} {d.source or ''}"
        for d in docs
    ])
    for pattern, name in INSTITUTIONAL_ATTRIBUTION_RULES:
        if pattern.search(sentence):
            if not pattern.search(combined_doc_text):
                return False, f"unsupported institutional attribution to '{name}'"
    return True, None


def check_claim_to_evidence(
    sentence: str,
    docs: list[RetrievedDocument],
    prediction_summary: PredictionHistorySummary | None = None,
) -> tuple[bool, str | None]:
    """Verify meaningful salient content term overlap between claim sentence and cited documents."""
    lower_sent = sentence.lower()
    tokens = set(re.findall(r"\b[a-z]+\b", lower_sent))
    is_meta_ref = bool(tokens & META_REFERENCE_TERMS)

    claim_terms = extract_salient_terms(sentence)
    if not claim_terms:
        # Check if sentence is a meta-reference to the source (e.g. "See [S1] for more info")
        if is_meta_ref:
            return True, None
        return False, "insufficient salient terms in claim to verify evidence"

    # If the sentence is a pure meta-reference/provenance statement describing sources without clinical claims
    if is_meta_ref and not (claim_terms - DISCOURSE_META_TERMS):
        return True, None

    doc_parts = [f"{d.content} {d.document_title or ''} {d.source_title or ''}" for d in docs]
    if prediction_summary and prediction_summary.predicted_class:
        doc_parts.append(prediction_summary.predicted_class.replace("_", " "))
    combined_doc_text = " ".join(doc_parts).lower()
    doc_terms = extract_salient_terms(combined_doc_text)

    overlap = claim_terms & doc_terms
    if len(overlap) < len(claim_terms):
        for ct in claim_terms - overlap:
            for dt in doc_terms:
                if (len(ct) >= 5 and (ct in dt or dt in ct)) or (len(ct) >= 6 and len(dt) >= 6 and ct[:5] == dt[:5]):
                    overlap.add(ct)
                    break

    ratio = len(overlap) / len(claim_terms)
    is_valid = len(overlap) >= 1 and (len(overlap) >= 2 or ratio >= 0.33)
    if not is_valid:
        return False, f"claim terms {claim_terms} have insufficient overlap with evidence (overlap: {overlap})"
    return True, None


def validate_and_filter_generated_response(
    raw_response: str,
    source_map: dict[str, RetrievedDocument],
    prediction_summary: PredictionHistorySummary | None = None,
    query: str = "",
) -> tuple[str, list[str], int, str | None]:
    """Perform sentence-level verification of citation tokens, attributions, and evidence entailment.

    Returns:
        (clean_answer, valid_citation_ids, unsupported_count, primary_refusal_reason)
    """
    lines = raw_response.split("\n")
    units: list[str] = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        sub_sents = re.split(r'(?<!\bMd\.)(?<!\bDr\.)(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\bvs\.)(?<!\bet al\.)(?<=[.!?])\s+(?=[A-Z0-9*#\-])', line_str)
        for s in sub_sents:
            s_clean = s.strip()
            if s_clean:
                units.append(s_clean)

    retained_units: list[str] = []
    retained_citation_ids: set[str] = set()
    unsupported_count = 0
    primary_failure_reason: str | None = None

    is_explicit_dev = is_explicit_developer_query(query)

    for unit in units:
        # If this is an ordinary medical/classifier query, suppress developer boilerplate units
        if not is_explicit_dev and is_developer_boilerplate_unit(unit):
            continue

        bracket_citations: list[str] = []
        for bracket_content in re.findall(r"\[([^\]]+)\]", unit):
            for match in re.finditer(r"\bS\d+\b", bracket_content):
                bracket_citations.append(match.group(0))

        def _clean_bracket(match: re.Match) -> str:
            content = match.group(1)
            tokens = re.findall(r"\bS\d+\b", content)
            valid = [t for t in tokens if t in source_map]
            return f"[{', '.join(valid)}]" if valid else ""

        if not bracket_citations:
            attr_ok, attr_err = check_institutional_attribution(unit, [])
            if not attr_ok:
                unsupported_count += 1
                if not primary_failure_reason:
                    primary_failure_reason = "developer_source_laundering" if (attr_err and "developer metadata" in attr_err) else "unsupported_attribution"
                continue
            clean_unit = re.sub(r"\[([^\]]+)\]", _clean_bracket, unit)
            if not is_explicit_dev:
                for dev_url_pat in DEVELOPER_URL_PATTERNS:
                    clean_unit = dev_url_pat.sub("", clean_unit)
            clean_unit = re.sub(r"[ \t]+", " ", clean_unit).strip()
            if clean_unit:
                retained_units.append(clean_unit)
            continue

        valid_cids = [cid for cid in bracket_citations if cid in source_map]
        invalid_cids = [cid for cid in bracket_citations if cid not in source_map]

        if invalid_cids:
            unsupported_count += len(invalid_cids)
            if not primary_failure_reason:
                primary_failure_reason = "citation_validation_failure"
            if not valid_cids:
                # All citations in this unit were invalid ([S99] etc.)
                continue

        cited_docs = [source_map[cid] for cid in valid_cids]

        attr_ok, attr_err = check_institutional_attribution(unit, cited_docs)
        if not attr_ok:
            unsupported_count += 1
            if not primary_failure_reason:
                primary_failure_reason = "developer_source_laundering" if (attr_err and "developer metadata" in attr_err) else "unsupported_attribution"
            continue

        ev_ok, ev_err = check_claim_to_evidence(unit, cited_docs, prediction_summary=prediction_summary)
        if not ev_ok:
            unsupported_count += 1
            if not primary_failure_reason:
                primary_failure_reason = "unsupported_claim_entailment"
            continue

        clean_unit = re.sub(r"\[([^\]]+)\]", _clean_bracket, unit)
        if not is_explicit_dev:
            for dev_url_pat in DEVELOPER_URL_PATTERNS:
                clean_unit = dev_url_pat.sub("", clean_unit)
        clean_unit = re.sub(r"[ \t]+", " ", clean_unit).strip()
        if clean_unit:
            retained_units.append(clean_unit)
            for cid in valid_cids:
                retained_citation_ids.add(cid)

    sorted_cids = sorted(
        list(retained_citation_ids),
        key=lambda x: int(x[1:]) if x[1:].isdigit() else 9999,
    )
    cleaned_text = "\n".join(retained_units).strip()
    return cleaned_text, sorted_cids, unsupported_count, primary_failure_reason


class GroundedRAGGenerator:
    """Production service for generating grounded medical explanations with citations."""

    def __init__(
        self,
        llm_client: GeminiClient | None = None,
        safety_evaluator: SafetyEvaluator | None = None,
        grounding_evaluator: GroundingEvaluator | None = None,
    ) -> None:
        self.settings = get_settings()
        self.llm_client = llm_client
        self.safety = safety_evaluator or SafetyEvaluator()
        self.grounding = grounding_evaluator or GroundingEvaluator(self.settings)

    async def generate_grounded_answer(
        self,
        query: str,
        context: RetrievedContext,
        prediction_summary: PredictionHistorySummary | None = None,
        chat_history: str = "",
        language: str = "en",
        request_id: str | None = None,
        telemetry: RAGTelemetryContext | None = None,
    ) -> GroundedAnswer:
        """Generate a grounded, citation-backed response to the user query."""
        if telemetry is None:
            telemetry = RAGTelemetryContext(
                request_id=request_id,
                chat_type="direct",
                query=query,
                language=language,
            )

        # Inherit stage latencies from context if present
        if hasattr(context, "classification_latency_ms"):
            telemetry.classification_ms = context.classification_latency_ms
        if hasattr(context, "retrieval_latency_ms"):
            telemetry.retrieval_ms = context.retrieval_latency_ms

        telemetry.retrieved_chunks = len(context.chunks)
        if context.query_scope:
            telemetry.domain = context.query_scope.domain.value if context.query_scope.domain else None
            telemetry.intent = context.query_scope.intent.value

        if context.chunks:
            sims = [c.similarity for c in context.chunks if c.similarity is not None]
            telemetry.top_similarity = max(sims) if sims else 0.0
            telemetry.mean_similarity = round(sum(sims) / len(sims), 4) if sims else 0.0

        request_intent = telemetry.intent or "unknown"
        request_domain = telemetry.domain or "unknown"

        # -------------------------------------------------------------
        # 1. Deterministic Pre-generation Safety Evaluation
        # -------------------------------------------------------------
        s_start = time.perf_counter()
        safety_eval = self.safety.evaluate_query(
            query=query,
            has_prediction=prediction_summary is not None,
        )
        telemetry.safety_ms = round((time.perf_counter() - s_start) * 1000, 2)

        if safety_eval.requires_deterministic_refusal:
            telemetry.safety_refused = True
            refusal_reason = safety_eval.boundary.value if safety_eval.boundary else "safety_refusal"
            telemetry.refusal_reason = refusal_reason
            telemetry.error_category = RAGErrorCategory.SAFETY_REFUSAL.value

            telemetry.record_event(
                EVENT_SAFETY_REFUSAL,
                boundary=refusal_reason,
                safety_ms=telemetry.safety_ms,
                intent=request_intent,
                has_prediction=prediction_summary is not None,
                skipped_gemini=True,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason=refusal_reason,
                error_category=RAGErrorCategory.SAFETY_REFUSAL.value,
            )

            refusal_message = safety_eval.refusal_message or "Request refused by safety policy."
            if refusal_reason == "prediction_conflict" and prediction_summary and prediction_summary.predicted_class:
                refusal_message = (
                    f"The generated response could not be verified against the authoritative classifier prediction. "
                    f"The recorded classification remains {prediction_summary.predicted_class} "
                    f"({round(prediction_summary.confidence * 100, 1)}% confidence). "
                    "Please review the prediction details or consult a qualified pathologist."
                )
            elif refusal_reason == SafetyBoundary.VISUAL_EVIDENCE.value and not safety_eval.refusal_message:
                refusal_message = VISUAL_EVIDENCE_REFUSAL_MESSAGE

            return GroundedAnswer(
                answer=refusal_message,
                citations=[],
                grounded=False,
                refusal_reason=refusal_reason,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        # -------------------------------------------------------------
        # 2. Deterministic Grounding & Relevance Evaluation (Phase 5.1)
        # -------------------------------------------------------------
        g_start = time.perf_counter()
        grounding_decision = self.grounding.evaluate(
            query=query,
            context=context,
            safety_eval=safety_eval,
        )
        telemetry.grounding_ms = round((time.perf_counter() - g_start) * 1000, 2)
        telemetry.top_similarity = grounding_decision.top_similarity
        telemetry.mean_similarity = grounding_decision.mean_similarity

        if grounding_decision.decision_reason == "conversational_greeting":
            is_bn = bool(re.search(r"[\u0980-\u09FF]", query))
            greeting_text = (
                "হ্যালো! আমি অনকোভিশন ক্লিনিক্যাল এআই সহকারী (OncoVision Clinical Assistant)। "
                "আমি ফুসফুস ও কোলন ক্যান্সারের হিস্টোপ্যাথলজিক্যাল প্যাটার্ন, টিস্যু ক্লাসিফিকেশন এবং প্যাথলজি সংক্রান্ত তথ্য প্রদানে সাহায্য করতে পারি। "
                "আজ আপনাকে কীভাবে সাহায্য করতে পারি?"
                if is_bn
                else
                "Hello! I am OncoVision's Clinical Knowledge Assistant. I specialize in histopathological "
                "analysis and educational evidence for lung and colon tissue classifications. "
                "How can I assist you with clinical knowledge or pathology characteristics today?"
            )
            telemetry.finish(grounded=True, citations=0, refusal_reason=None)
            return GroundedAnswer(
                answer=greeting_text,
                citations=[],
                grounded=True,
                refusal_reason=None,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        if not grounding_decision.is_eligible:
            if grounding_decision.decision_reason == "empty_retrieval":
                if is_meta_source_query(query):
                    refusal_text = (
                        "No supporting medical source context is currently available for this query, "
                        "so no literature sources can be cited."
                    )
                else:
                    refusal_text = (
                        "I don't have enough relevant information in the current OncoVision knowledge base "
                        "to answer that reliably."
                    )
                refusal_reason = "no_relevant_knowledge_found"
            else:
                refusal_text = (
                    "The available OncoVision knowledge base provides only limited information on this point, "
                    "so I can't make a reliable claim beyond the retrieved evidence."
                )
                refusal_reason = grounding_decision.decision_reason

            telemetry.refusal_reason = refusal_reason
            telemetry.record_event(
                EVENT_GROUNDING_REJECTED,
                decision_reason=grounding_decision.decision_reason,
                top_similarity=grounding_decision.top_similarity,
                mean_similarity=grounding_decision.mean_similarity,
                threshold_applied=grounding_decision.threshold_applied,
                grounding_ms=telemetry.grounding_ms,
                skipped_gemini=True,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason=refusal_reason,
            )

            return GroundedAnswer(
                answer=refusal_text,
                citations=[],
                grounded=False,
                refusal_reason=refusal_reason,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        telemetry.record_event(
            EVENT_GROUNDING_ACCEPTED,
            decision_reason=grounding_decision.decision_reason,
            top_similarity=grounding_decision.top_similarity,
            mean_similarity=grounding_decision.mean_similarity,
            threshold_applied=grounding_decision.threshold_applied,
            domain_compatible=grounding_decision.domain_compatible,
            class_compatible=grounding_decision.class_compatible,
            grounding_ms=telemetry.grounding_ms,
        )

        # -------------------------------------------------------------
        # 3. Prompt Construction with Numbered Source Mapping
        # -------------------------------------------------------------
        context_text, source_map = format_grounded_context_sources(context.chunks)
        user_prompt = build_grounded_user_prompt(
            user_message=query,
            retrieved_context_text=context_text,
            prediction_summary=prediction_summary,
            chat_history=chat_history,
            safety_guidance=safety_eval.boundary_guidance,
            language=language,
        )

        # -------------------------------------------------------------
        # 4. Async Gemini Generation with Timeout & Retries
        # -------------------------------------------------------------
        client = self.llm_client or get_gemini_client(
            api_key=self.settings.GOOGLE_API_KEY,
            model_name=self.settings.RAG_GENERATION_MODEL,
        )

        telemetry.skipped_gemini = False
        telemetry.generation_model = self.settings.RAG_GENERATION_MODEL
        telemetry.record_event(
            EVENT_GENERATION_STARTED,
            model=self.settings.RAG_GENERATION_MODEL,
            context_chunks=len(context.chunks),
        )

        raw_response = ""
        gen_start = time.perf_counter()
        try:
            raw_response = await asyncio.wait_for(
                client.generate(
                    prompt=user_prompt,
                    system_instruction=GROUNDED_RAG_SYSTEM_PROMPT,
                    temperature=self.settings.RAG_GENERATION_TEMPERATURE,
                    max_output_tokens=self.settings.RAG_GENERATION_MAX_OUTPUT_TOKENS,
                ),
                timeout=self.settings.RAG_GENERATION_TIMEOUT,
            )
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            telemetry.record_event(
                EVENT_GENERATION_COMPLETED,
                model=self.settings.RAG_GENERATION_MODEL,
                generation_ms=telemetry.generation_ms,
                response_length=len(raw_response),
            )
        except asyncio.TimeoutError:
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            telemetry.error_category = RAGErrorCategory.GENERATION_TIMEOUT.value
            telemetry.record_event(
                EVENT_GENERATION_TIMEOUT,
                model=self.settings.RAG_GENERATION_MODEL,
                timeout_sec=self.settings.RAG_GENERATION_TIMEOUT,
                generation_ms=telemetry.generation_ms,
                error_category=RAGErrorCategory.GENERATION_TIMEOUT.value,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason="generation_timeout",
                error_category=RAGErrorCategory.GENERATION_TIMEOUT.value,
            )
            return GroundedAnswer(
                answer="The request timed out while generating a grounded explanation. Please try again.",
                citations=[],
                grounded=False,
                refusal_reason="generation_timeout",
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )
        except Exception as e:
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            telemetry.error_category = RAGErrorCategory.GENERATION_API_ERROR.value
            logger.error("Gemini grounded generation failed: %s", e, exc_info=True)
            telemetry.record_event(
                EVENT_GENERATION_FAILED,
                model=self.settings.RAG_GENERATION_MODEL,
                generation_ms=telemetry.generation_ms,
                error_category=RAGErrorCategory.GENERATION_API_ERROR.value,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason="api_error",
                error_category=RAGErrorCategory.GENERATION_API_ERROR.value,
            )
            return GroundedAnswer(
                answer="A service error occurred while generating the explanation. Please try again.",
                citations=[],
                grounded=False,
                refusal_reason="api_error",
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        return self._validate_and_finalize_grounded_answer(
            raw_response=raw_response,
            source_map=source_map,
            safety_eval=safety_eval,
            grounding_decision=grounding_decision,
            prediction_summary=prediction_summary,
            query=query,
            context=context,
            telemetry=telemetry,
        )

    async def generate_grounded_stream(
        self,
        query: str,
        context: RetrievedContext,
        prediction_summary: PredictionHistorySummary | None = None,
        chat_history: str = "",
        language: str = "en",
        request_id: str | None = None,
        telemetry: RAGTelemetryContext | None = None,
        raw_request: Any | None = None,
    ) -> GroundedAnswer:
        """Generate a grounded, citation-backed response via Gemini streaming with server-side buffering and validation."""
        if telemetry is None:
            telemetry = RAGTelemetryContext(
                request_id=request_id,
                chat_type="direct",
                query=query,
                language=language,
            )

        if hasattr(context, "classification_latency_ms"):
            telemetry.classification_ms = context.classification_latency_ms
        if hasattr(context, "retrieval_latency_ms"):
            telemetry.retrieval_ms = context.retrieval_latency_ms

        telemetry.retrieved_chunks = len(context.chunks)
        if context.query_scope:
            telemetry.domain = context.query_scope.domain.value if context.query_scope.domain else None
            telemetry.intent = context.query_scope.intent.value

        if context.chunks:
            sims = [c.similarity for c in context.chunks if c.similarity is not None]
            telemetry.top_similarity = max(sims) if sims else 0.0
            telemetry.mean_similarity = round(sum(sims) / len(sims), 4) if sims else 0.0

        request_intent = telemetry.intent or "unknown"
        request_domain = telemetry.domain or "unknown"

        # 1. Deterministic Pre-generation Safety Evaluation
        s_start = time.perf_counter()
        safety_eval = self.safety.evaluate_query(
            query=query,
            has_prediction=prediction_summary is not None,
        )
        telemetry.safety_ms = round((time.perf_counter() - s_start) * 1000, 2)

        if safety_eval.requires_deterministic_refusal:
            telemetry.safety_refused = True
            refusal_reason = safety_eval.boundary.value if safety_eval.boundary else "safety_refusal"
            telemetry.refusal_reason = refusal_reason
            telemetry.error_category = RAGErrorCategory.SAFETY_REFUSAL.value

            telemetry.record_event(
                EVENT_SAFETY_REFUSAL,
                boundary=refusal_reason,
                safety_ms=telemetry.safety_ms,
                intent=request_intent,
                has_prediction=prediction_summary is not None,
                skipped_gemini=True,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason=refusal_reason,
                error_category=RAGErrorCategory.SAFETY_REFUSAL.value,
            )

            refusal_message = safety_eval.refusal_message or "Request refused by safety policy."
            if refusal_reason == "prediction_conflict" and prediction_summary and prediction_summary.predicted_class:
                refusal_message = (
                    f"The generated response could not be verified against the authoritative classifier prediction. "
                    f"The recorded classification remains {prediction_summary.predicted_class} "
                    f"({round(prediction_summary.confidence * 100, 1)}% confidence). "
                    "Please review the prediction details or consult a qualified pathologist."
                )
            elif refusal_reason == SafetyBoundary.VISUAL_EVIDENCE.value and not safety_eval.refusal_message:
                refusal_message = VISUAL_EVIDENCE_REFUSAL_MESSAGE

            return GroundedAnswer(
                answer=refusal_message,
                citations=[],
                grounded=False,
                refusal_reason=refusal_reason,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        # 2. Deterministic Grounding & Relevance Evaluation
        g_start = time.perf_counter()
        grounding_decision = self.grounding.evaluate(
            query=query,
            context=context,
            safety_eval=safety_eval,
        )
        telemetry.grounding_ms = round((time.perf_counter() - g_start) * 1000, 2)
        telemetry.top_similarity = grounding_decision.top_similarity
        telemetry.mean_similarity = grounding_decision.mean_similarity

        if grounding_decision.decision_reason == "conversational_greeting":
            is_bn = bool(re.search(r"[\u0980-\u09FF]", query))
            greeting_text = (
                "হ্যালো! আমি অনকোভিশন ক্লিনিক্যাল এআই সহকারী (OncoVision Clinical Assistant)। "
                "আমি ফুসফুস ও কোলন ক্যান্সারের হিস্টোপ্যাথলজিক্যাল প্যাটার্ন, টিস্যু ক্লাসিফিকেশন এবং প্যাথলজি সংক্রান্ত তথ্য প্রদানে সাহায্য করতে পারি। "
                "আজ আপনাকে কীভাবে সাহায্য করতে পারি?"
                if is_bn
                else
                "Hello! I am OncoVision's Clinical Knowledge Assistant. I specialize in histopathological "
                "analysis and educational evidence for lung and colon tissue classifications. "
                "How can I assist you with clinical knowledge or pathology characteristics today?"
            )
            telemetry.finish(grounded=True, citations=0, refusal_reason=None)
            return GroundedAnswer(
                answer=greeting_text,
                citations=[],
                grounded=True,
                refusal_reason=None,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        if not grounding_decision.is_eligible:
            if grounding_decision.decision_reason == "empty_retrieval":
                if is_meta_source_query(query):
                    refusal_text = (
                        "No supporting medical source context is currently available for this query, "
                        "so no literature sources can be cited."
                    )
                else:
                    refusal_text = (
                        "I don't have enough relevant information in the current OncoVision knowledge base "
                        "to answer that reliably."
                    )
                refusal_reason = "no_relevant_knowledge_found"
            else:
                refusal_text = (
                    "The available OncoVision knowledge base provides only limited information on this point, "
                    "so I can't make a reliable claim beyond the retrieved evidence."
                )
                refusal_reason = grounding_decision.decision_reason

            telemetry.refusal_reason = refusal_reason
            telemetry.record_event(
                EVENT_GROUNDING_REJECTED,
                decision_reason=grounding_decision.decision_reason,
                top_similarity=grounding_decision.top_similarity,
                mean_similarity=grounding_decision.mean_similarity,
                threshold_applied=grounding_decision.threshold_applied,
                grounding_ms=telemetry.grounding_ms,
                skipped_gemini=True,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason=refusal_reason,
            )

            return GroundedAnswer(
                answer=refusal_text,
                citations=[],
                grounded=False,
                refusal_reason=refusal_reason,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        telemetry.record_event(
            EVENT_GROUNDING_ACCEPTED,
            decision_reason=grounding_decision.decision_reason,
            top_similarity=grounding_decision.top_similarity,
            mean_similarity=grounding_decision.mean_similarity,
            threshold_applied=grounding_decision.threshold_applied,
            domain_compatible=grounding_decision.domain_compatible,
            class_compatible=grounding_decision.class_compatible,
            grounding_ms=telemetry.grounding_ms,
        )

        # 3. Prompt Construction
        context_text, source_map = format_grounded_context_sources(context.chunks)
        user_prompt = build_grounded_user_prompt(
            user_message=query,
            retrieved_context_text=context_text,
            prediction_summary=prediction_summary,
            chat_history=chat_history,
            safety_guidance=safety_eval.boundary_guidance,
            language=language,
        )

        # 4. Async Gemini Streaming Generation with Server-Side Buffering
        client = self.llm_client or get_gemini_client(
            api_key=self.settings.GOOGLE_API_KEY,
            model_name=self.settings.RAG_GENERATION_MODEL,
        )

        telemetry.skipped_gemini = False
        telemetry.generation_model = self.settings.RAG_GENERATION_MODEL
        telemetry.record_event(
            EVENT_GENERATION_STARTED,
            model=self.settings.RAG_GENERATION_MODEL,
            context_chunks=len(context.chunks),
        )

        chunk_buffer: list[str] = []
        gen_start = time.perf_counter()
        try:
            stream_iter = client.generate_stream(
                prompt=user_prompt,
                system_instruction=GROUNDED_RAG_SYSTEM_PROMPT,
                temperature=self.settings.RAG_GENERATION_TEMPERATURE,
                max_output_tokens=self.settings.RAG_GENERATION_MAX_OUTPUT_TOKENS,
            )
            async for chunk in stream_iter:
                if raw_request and await raw_request.is_disconnected():
                    logger.info("Client disconnected during LLM stream generation. Aborting.")
                    raise asyncio.CancelledError()
                if chunk:
                    chunk_buffer.append(chunk)

            raw_response = "".join(chunk_buffer)
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            telemetry.record_event(
                EVENT_GENERATION_COMPLETED,
                model=self.settings.RAG_GENERATION_MODEL,
                generation_ms=telemetry.generation_ms,
                response_length=len(raw_response),
            )
        except asyncio.CancelledError:
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            logger.info("Grounded stream generation cancelled by client disconnect.")
            raise
        except asyncio.TimeoutError:
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            telemetry.error_category = RAGErrorCategory.GENERATION_TIMEOUT.value
            telemetry.record_event(
                EVENT_GENERATION_TIMEOUT,
                model=self.settings.RAG_GENERATION_MODEL,
                timeout_sec=self.settings.RAG_GENERATION_TIMEOUT,
                generation_ms=telemetry.generation_ms,
                error_category=RAGErrorCategory.GENERATION_TIMEOUT.value,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason="generation_timeout",
                error_category=RAGErrorCategory.GENERATION_TIMEOUT.value,
            )
            return GroundedAnswer(
                answer="The request timed out while generating a grounded explanation. Please try again.",
                citations=[],
                grounded=False,
                refusal_reason="generation_timeout",
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )
        except Exception as e:
            telemetry.generation_ms = round((time.perf_counter() - gen_start) * 1000, 2)
            telemetry.error_category = RAGErrorCategory.GENERATION_API_ERROR.value
            logger.error("Gemini grounded stream generation failed: %s", e, exc_info=True)
            telemetry.record_event(
                EVENT_GENERATION_FAILED,
                model=self.settings.RAG_GENERATION_MODEL,
                generation_ms=telemetry.generation_ms,
                error_category=RAGErrorCategory.GENERATION_API_ERROR.value,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason="api_error",
                error_category=RAGErrorCategory.GENERATION_API_ERROR.value,
            )
            return GroundedAnswer(
                answer="A service error occurred while generating the explanation. Please try again.",
                citations=[],
                grounded=False,
                refusal_reason="api_error",
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        return self._validate_and_finalize_grounded_answer(
            raw_response=raw_response,
            source_map=source_map,
            safety_eval=safety_eval,
            grounding_decision=grounding_decision,
            prediction_summary=prediction_summary,
            query=query,
            context=context,
            telemetry=telemetry,
        )

    def _validate_and_finalize_grounded_answer(
        self,
        raw_response: str,
        source_map: dict[str, RetrievedDocument],
        safety_eval: SafetyEvaluation,
        grounding_decision: GroundingDecision,
        prediction_summary: PredictionHistorySummary | None,
        query: str,
        context: RetrievedContext,
        telemetry: RAGTelemetryContext,
    ) -> GroundedAnswer:
        """Execute post-generation medical safety, prediction immutability, citation integrity,
        and grounding validation on the complete server-buffered response."""
        # -------------------------------------------------------------
        # 5. Immediate Post-generation Medical Safety & Prediction Immutability Check
        # (Preserve Phase 6 fail-closed boundaries: direct diagnosis, prescriptions,
        # staging/biomarker claims from H&E alone, classifier overrides, prompt leaks)
        # -------------------------------------------------------------
        pre_clean_for_safety = re.sub(r'https?://[^\s]+', '', raw_response)
        pre_clean_for_safety = re.sub(r'\[\s*(?:SYSTEM|SOURCE|Ref\s*\d+|\d+)\s*\]', '', pre_clean_for_safety, flags=re.IGNORECASE)

        is_safe, safety_violation = self.safety.validate_answer(
            pre_clean_for_safety,
            boundary=safety_eval.boundary,
            prediction_summary=prediction_summary,
        )
        if not is_safe:
            logger.warning("Post-generation safety check flagged answer: %s", safety_violation)
            telemetry.safety_refused = True

            # Fail-closed refusal determination (Gate 6.3-B, Gate 6.3-C)
            if "contradicts authoritative classifier prediction" in str(safety_violation) or "claims conflicting class" in str(safety_violation):
                refusal_reason = "prediction_conflict"
                if prediction_summary and prediction_summary.predicted_class:
                    refusal_message = (
                        f"The generated response could not be verified against the authoritative classifier prediction. "
                        f"The recorded classification remains {prediction_summary.predicted_class} "
                        f"({round(prediction_summary.confidence * 100, 1)}% confidence). "
                        "Please review the prediction details or consult a qualified pathologist."
                    )
                else:
                    refusal_message = PREDICTION_CONFLICT_MESSAGE
            elif safety_eval.boundary == SafetyBoundary.DIAGNOSIS or "direct diagnosis" in str(safety_violation):
                refusal_reason = SafetyBoundary.DIAGNOSIS.value
                refusal_message = DIAGNOSIS_REFUSAL_MESSAGE
            elif safety_eval.boundary == SafetyBoundary.TREATMENT or "prescription" in str(safety_violation):
                refusal_reason = SafetyBoundary.TREATMENT.value
                refusal_message = TREATMENT_REFUSAL_MESSAGE
            elif safety_eval.boundary == SafetyBoundary.STAGING or "staging" in str(safety_violation):
                refusal_reason = SafetyBoundary.STAGING.value
                refusal_message = STAGING_BOUNDARY_GUIDANCE
            elif safety_eval.boundary == SafetyBoundary.BIOMARKER or "biomarker" in str(safety_violation):
                refusal_reason = SafetyBoundary.BIOMARKER.value
                refusal_message = BIOMARKER_BOUNDARY_GUIDANCE
            elif safety_eval.boundary == SafetyBoundary.VISUAL_EVIDENCE or "visual observation" in str(safety_violation):
                refusal_reason = SafetyBoundary.VISUAL_EVIDENCE.value
                refusal_message = VISUAL_EVIDENCE_REFUSAL_MESSAGE
            elif safety_eval.boundary == SafetyBoundary.DEVELOPER_ATTRIBUTION or "developer metadata" in str(safety_violation):
                refusal_reason = SafetyBoundary.DEVELOPER_ATTRIBUTION.value
                refusal_message = DEVELOPER_ATTRIBUTION_REFUSAL_MESSAGE
            elif "leakage" in str(safety_violation):
                refusal_reason = "security_leakage_prevented"
                refusal_message = (
                    "OncoVision cannot execute instruction override, prompt inspection, or safety bypass requests. "
                    "All interactions must adhere to clinical safety and system integrity boundaries."
                )
            else:
                refusal_reason = "post_generation_safety_violation"
                refusal_message = (
                    "The generated response contained clinical assertions that exceed OncoVision safety boundaries. "
                    "OncoVision is strictly educational and non-diagnostic and cannot provide clinical diagnoses, "
                    "personalized treatment protocols, or definitive staging."
                )

            telemetry.refusal_reason = refusal_reason
            telemetry.error_category = RAGErrorCategory.SAFETY_REFUSAL.value
            telemetry.record_event(
                EVENT_SAFETY_REFUSAL,
                boundary=refusal_reason,
                violation=safety_violation,
                post_generation=True,
            )
            telemetry.finish(
                grounded=False,
                citations=0,
                refusal_reason=refusal_reason,
                error_category=RAGErrorCategory.SAFETY_REFUSAL.value,
            )

            # FAIL CLOSED: Do not return unsafe generated content or citations!
            return GroundedAnswer(
                answer=refusal_message,
                citations=[],
                grounded=False,
                refusal_reason=refusal_reason,
                scope=context.query_scope,
                latency_ms=telemetry.total_latency_ms,
                latencies=telemetry.get_latency_breakdown(),
                request_id=telemetry.request_id,
            )

        # -------------------------------------------------------------
        # 6. Sentence-Level Citation Integrity, Attribution & Evidence Validation
        # -------------------------------------------------------------
        cit_start = time.perf_counter()
        clean_answer, unique_cids, unsupported_count, primary_failure_reason = (
            validate_and_filter_generated_response(
                raw_response, source_map, prediction_summary=prediction_summary, query=query
            )
        )

        valid_citations: list[Citation] = []
        for cid in unique_cids:
            doc = source_map[cid]
            valid_citations.append(
                Citation(
                    source_id=cid,
                    document_id=doc.document_id or "unknown",
                    document_title=doc.document_title or doc.topic or "Medical Document",
                    source_title=doc.source_title or doc.source or "OncoVision Medical Knowledge Base",
                    source_url=doc.source_url or "",
                    source_tier=doc.source_tier,
                    domain=doc.domain,
                )
            )

        # Sanitize raw external URLs embedded directly in answer text:
        # Preserves legitimate medical source URLs, but strips developer or unverified external URLs
        is_explicit_dev = is_explicit_developer_query(query)
        if not is_explicit_dev:
            def _filter_url(match: re.Match) -> str:
                full_match = match.group(0)
                clean_url = full_match.rstrip(".,;!?:)]")
                trail = full_match[len(clean_url):]
                if is_medical_source_url(clean_url, source_map):
                    return full_match
                return trail

            clean_answer = re.sub(r'https?://[^\s]+', _filter_url, clean_answer)
            clean_answer = re.sub(r'\[([^\]]*)\]\(\s*\)', r'\1', clean_answer)
        clean_answer = re.sub(r'[ \t]+', ' ', clean_answer)
        clean_answer = re.sub(r'\n{3,}', '\n\n', clean_answer).strip()

        telemetry.citation_validation_ms = round((time.perf_counter() - cit_start) * 1000, 2)
        telemetry.record_event(
            EVENT_CITATION_VALIDATION,
            total_citations_found=len(unique_cids) + unsupported_count,
            valid_citations_count=len(valid_citations),
            unsupported_citations_stripped=unsupported_count,
            citation_validation_ms=telemetry.citation_validation_ms,
        )

        # -------------------------------------------------------------
        # 7. Grounding Determination & Request Completion
        # -------------------------------------------------------------
        is_grounded = bool(
            grounding_decision.is_eligible
            and (valid_citations or is_explicit_dev)
            and len(clean_answer.strip()) > 0
        )

        fin_refusal_reason: str | None = None
        if not is_grounded:
            if primary_failure_reason:
                fin_refusal_reason = primary_failure_reason
            elif unsupported_count > 0 and not valid_citations:
                fin_refusal_reason = "citation_validation_failure"
            elif not valid_citations:
                fin_refusal_reason = "unsupported_claims_without_citations"

            # Fail closed: do not expose ungrounded / unsupported generated content for medical queries
            if not clean_answer.strip() or (not valid_citations and not is_explicit_dev):
                valid_citations = []
                if fin_refusal_reason == "developer_source_laundering":
                    clean_answer = DEVELOPER_ATTRIBUTION_REFUSAL_MESSAGE
                else:
                    clean_answer = (
                        "The available OncoVision knowledge base provides only limited information "
                        "on this point, so I cannot make a reliable claim beyond the retrieved evidence."
                    )

        telemetry.finish(
            grounded=is_grounded,
            citations=len(valid_citations),
            refusal_reason=fin_refusal_reason,
        )

        return GroundedAnswer(
            answer=clean_answer.strip(),
            citations=valid_citations,
            grounded=is_grounded,
            refusal_reason=fin_refusal_reason,
            scope=context.query_scope,
            latency_ms=telemetry.total_latency_ms,
            latencies=telemetry.get_latency_breakdown(),
            request_id=telemetry.request_id,
        )
