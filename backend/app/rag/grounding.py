"""Deterministic RAG Grounding & Relevance Evaluator (Phase 5.1).

Evaluates whether retrieved knowledge is sufficiently relevant to ground
a trustworthy, citation-backed answer. Prevents false claims of grounding
for out-of-domain queries, weak retrieval matches, scope mismatches,
or safety refusals.

Principles:
- Non-empty chunks != grounded answer.
- Grounding eligibility is deterministic, fast, and backend-controlled (0 extra LLM calls).
- Conservative policy: weak or unrelated retrieval defaults to grounded=False.
"""

from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.core.settings import Settings, get_settings
from app.rag.classifier import ClassScope, QueryDomain, QueryIntent, QueryScope
from app.rag.provenance import is_explicit_developer_query
from app.rag.retriever import RetrievedContext
from app.rag.safety import SafetyEvaluation

logger = logging.getLogger(__name__)


class GroundingDecision(BaseModel):
    """Deterministic decision on whether retrieval suffices for grounded generation."""

    model_config = ConfigDict(frozen=True)

    is_eligible: bool = Field(
        ...,
        description="True if retrieval is relevant and sufficient to ground a faithful response.",
    )
    decision_reason: str = Field(
        ...,
        description="Deterministic reason (e.g. 'relevant_retrieval', 'out_of_domain_query', 'insufficient_similarity').",
    )
    top_similarity: float = Field(
        default=0.0,
        description="Cosine similarity of the highest ranked retrieved chunk.",
    )
    mean_similarity: float = Field(
        default=0.0,
        description="Average cosine similarity across all retrieved chunks.",
    )
    domain_compatible: bool = Field(
        default=True,
        description="Whether retrieved chunk domains are compatible with classified query domain.",
    )
    class_compatible: bool = Field(
        default=True,
        description="Whether retrieved chunks correspond to the explicit class scope when requested.",
    )
    threshold_applied: float = Field(
        default=0.0,
        description="The minimum similarity threshold enforced for this query type.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic metadata for evaluation and telemetry logging.",
    )


class GroundingEvaluator:
    """Deterministic, fast, backend-controlled evaluator for RAG grounding eligibility.
    
    Adheres strictly to Phase 5.1 requirements:
    1. Safety refusal -> grounded = False
    2. Empty retrieval -> grounded = False
    3. Weak retrieval (below floor) -> grounded = False
    4. Out-of-domain / non-medical query -> grounded = False
    5. Domain mismatch -> grounded = False
    6. Strong, relevant, compatible retrieval -> grounded = True (eligible)
    """

    # Domain compatibility matrix mapping query domain to compatible chunk domains
    _DOMAIN_COMPATIBILITY_MAP: dict[QueryDomain, set[str]] = {
        QueryDomain.LUNG: {
            "lung",
            "histopathology",
            "general_oncology",
            "clinical_explanation",
            "classifier_context",
            "safety_policy",
        },
        QueryDomain.COLON: {
            "colon",
            "histopathology",
            "general_oncology",
            "clinical_explanation",
            "classifier_context",
            "safety_policy",
        },
        QueryDomain.COMPARISON: {
            "comparison",
            "lung",
            "colon",
            "classifier_context",
            "histopathology",
            "general_oncology",
            "safety_policy",
        },
        QueryDomain.SAFETY_POLICY: {
            "safety_policy",
            "general_oncology",
            "clinical_explanation",
            "classifier_context",
            "lung",
            "colon",
        },
        QueryDomain.HISTOPATHOLOGY: {
            "histopathology",
            "general_oncology",
            "lung",
            "colon",
            "clinical_explanation",
            "classifier_context",
            "safety_policy",
        },
        QueryDomain.GENERAL_ONCOLOGY: {
            "general_oncology",
            "histopathology",
            "clinical_explanation",
            "lung",
            "colon",
            "safety_policy",
            "classifier_context",
        },
        QueryDomain.CLASSIFIER_CONTEXT: {
            "classifier_context",
            "lung",
            "colon",
            "histopathology",
            "general_oncology",
            "clinical_explanation",
            "safety_policy",
        },
        QueryDomain.DEVELOPER_INFO: {
            "developer_info",
            "platform_info",
            "classifier_context",
        },
        QueryDomain.PLATFORM_INFO: {
            "platform_info",
            "developer_info",
            "classifier_context",
        },
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(
        self,
        query: str,
        context: RetrievedContext,
        safety_eval: SafetyEvaluation | None = None,
    ) -> GroundingDecision:
        """Evaluate retrieval relevance and return a deterministic GroundingDecision."""
        # 0. Gate: Conversational Greetings & Assistant Identity
        query_scope = context.query_scope or QueryScope(
            domain=None,
            confidence=0.0,
            intent=QueryIntent.GENERAL_KNOWLEDGE,
        )
        if query_scope.intent == QueryIntent.CONVERSATIONAL:
            return GroundingDecision(
                is_eligible=True,
                decision_reason="conversational_greeting",
                top_similarity=1.0,
                mean_similarity=1.0,
                domain_compatible=True,
                class_compatible=True,
                threshold_applied=0.0,
                details={"gate": "conversational_greeting"},
            )

        # 1. Gate: Pre-generation Safety Refusal
        if safety_eval and safety_eval.requires_deterministic_refusal:
            reason = safety_eval.boundary.value if safety_eval.boundary else "safety_refusal"
            return GroundingDecision(
                is_eligible=False,
                decision_reason=reason,
                top_similarity=0.0,
                mean_similarity=0.0,
                domain_compatible=False,
                class_compatible=False,
                threshold_applied=0.0,
                details={"gate": "safety_refusal", "boundary": reason},
            )

        # 2. Gate: Empty Context / No Knowledge Found
        if not context.chunks or context.reason in {
            "no_relevant_knowledge_found",
            "empty_query",
            "empty_knowledge_base",
            "retrieval_error",
        }:
            return GroundingDecision(
                is_eligible=False,
                decision_reason="empty_retrieval",
                top_similarity=0.0,
                mean_similarity=0.0,
                domain_compatible=False,
                class_compatible=False,
                threshold_applied=0.0,
                details={"gate": "empty_context", "context_reason": context.reason},
            )

        # Compute numerical metrics
        sims = [chunk.similarity for chunk in context.chunks if chunk.similarity is not None]
        top_sim = max(sims) if sims else 0.0
        mean_sim = (sum(sims) / len(sims)) if sims else 0.0

        # 3. Gate: Unclassified / Out-of-Domain Query Gate
        # If the query had no medical domain, no explicit class match, and no safety context,
        # it is an out-of-scope non-medical question (e.g. recipes, programming, math, capital cities).
        # In a dense vector space, background similarities for such queries hover around 0.55-0.65.
        # They must be evaluated against the strict strong grounding threshold (default 0.82).
        is_dev_query = is_explicit_developer_query(query)
        is_unclassified_query = (
            query_scope.domain is None
            and not query_scope.requires_safety_context
            and not query_scope.class_scopes
            and not is_dev_query
            and query_scope.intent == QueryIntent.GENERAL_KNOWLEDGE
        )

        if is_dev_query:
            min_required_threshold = self.settings.RAG_SIMILARITY_THRESHOLD
        elif is_unclassified_query:
            min_required_threshold = self.settings.RAG_STRONG_GROUNDING_SIMILARITY
        else:
            min_required_threshold = self.settings.RAG_MIN_GROUNDING_SIMILARITY

        if top_sim < min_required_threshold:
            reason = "out_of_domain_query" if is_unclassified_query else "insufficient_similarity"
            return GroundingDecision(
                is_eligible=False,
                decision_reason=reason,
                top_similarity=round(top_sim, 4),
                mean_similarity=round(mean_sim, 4),
                domain_compatible=False,
                class_compatible=False,
                threshold_applied=min_required_threshold,
                details={
                    "gate": "similarity_floor",
                    "is_unclassified": is_unclassified_query,
                    "top_similarity": top_sim,
                    "required_threshold": min_required_threshold,
                },
            )

        # 4. Gate: Domain Compatibility Check
        domain_compatible = True
        if query_scope.domain is not None and not is_dev_query:
            allowed_chunk_domains = self._DOMAIN_COMPATIBILITY_MAP.get(query_scope.domain, set())
            retrieved_domains = {c.domain for c in context.chunks if c.domain}
            if allowed_chunk_domains and not (retrieved_domains & allowed_chunk_domains):
                domain_compatible = False
                return GroundingDecision(
                    is_eligible=False,
                    decision_reason="domain_mismatch",
                    top_similarity=round(top_sim, 4),
                    mean_similarity=round(mean_sim, 4),
                    domain_compatible=False,
                    class_compatible=False,
                    threshold_applied=min_required_threshold,
                    details={
                        "gate": "domain_mismatch",
                        "query_domain": query_scope.domain.value,
                        "retrieved_domains": list(retrieved_domains),
                    },
                )

        # 5. Gate: Class Scope Compatibility (Soft validation for explicit matches)
        class_compatible = True
        if query_scope.explicit_class_match and query_scope.class_scopes:
            target_class_values = {cs.value for cs in query_scope.class_scopes}
            # Verify that at least one chunk pertains to the explicit class scope
            has_class_evidence = any(
                any(tc in (c.topic or "").lower() or tc in (c.source or "").lower() for tc in target_class_values)
                for c in context.chunks
            )
            # If explicit class was requested but zero chunks relate to it, and similarity is borderline (<0.88), reject
            if not has_class_evidence and top_sim < 0.88:
                class_compatible = False
                return GroundingDecision(
                    is_eligible=False,
                    decision_reason="class_mismatch",
                    top_similarity=round(top_sim, 4),
                    mean_similarity=round(mean_sim, 4),
                    domain_compatible=domain_compatible,
                    class_compatible=False,
                    threshold_applied=min_required_threshold,
                    details={
                        "gate": "class_mismatch",
                        "target_classes": list(target_class_values),
                    },
                )

        # 6. All gates passed: Sufficient, relevant, domain-compatible retrieval
        return GroundingDecision(
            is_eligible=True,
            decision_reason="relevant_retrieval",
            top_similarity=round(top_sim, 4),
            mean_similarity=round(mean_sim, 4),
            domain_compatible=domain_compatible,
            class_compatible=class_compatible,
            threshold_applied=min_required_threshold,
            details={
                "top_similarity": top_sim,
                "mean_similarity": mean_sim,
                "retrieved_count": len(context.chunks),
            },
        )
