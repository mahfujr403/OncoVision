"""Strongly typed contracts for grounded RAG generation and citations (Phase 4).

Defines the output shapes for verified source citations and grounded answers.
Crucially, confidence fields are omitted or restricted to non-diagnostic metrics
to guarantee the LLM never presents itself as a diagnostic classifier.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.rag.classifier import QueryScope

_DEFAULT_MEDICAL_DISCLAIMER = (
    "This information is AI-generated for educational and research purposes only. "
    "It is not medical advice, a pathological diagnosis, or a treatment recommendation. "
    "Always consult a qualified oncologist or board-certified pathologist for clinical decisions."
)


class Citation(BaseModel):
    """Trusted citation derived directly and solely from retrieved document provenance.
    
    All URL and title fields are populated from verified backend metadata, never
    trusted from raw LLM output.
    """

    model_config = ConfigDict(frozen=True)

    source_id: str = Field(
        ...,
        description="Bracketed source reference key used in generated text (e.g. 'S1').",
    )
    document_id: str = Field(
        ...,
        description="Deterministic document identifier from knowledge base.",
    )
    document_title: str = Field(
        ...,
        description="Canonical human-readable document title.",
    )
    source_title: str = Field(
        ...,
        description="Underlying reference publication or guideline title.",
    )
    source_url: str = Field(
        ...,
        description="Clickable authoritative reference URL.",
    )
    source_tier: int | None = Field(
        default=None,
        description="Evidence hierarchy tier (1: Guidelines, 2: StatPearls/Textbooks, 3: Literature).",
    )
    domain: str | None = Field(
        default=None,
        description="Medical domain (e.g. colon, lung, general_oncology).",
    )


class GroundedAnswer(BaseModel):
    """Strongly typed grounded generation response.
    
    Guarantees that:
    - Generated answers reference only verified retrieved sources.
    - Citations reflect backend provenance records.
    - The LLM is strictly non-diagnostic.
    """

    answer: str = Field(
        ...,
        description="The grounded answer text, containing valid [S#] citations.",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="List of verified citations corresponding to [S#] references in the answer.",
    )
    grounded: bool = Field(
        default=False,
        description="True if the response is verified to be grounded in retrieved context.",
    )
    refusal_reason: str | None = Field(
        default=None,
        description="Reason for refusing or bounding the answer (e.g. 'diagnosis_boundary', 'no_relevant_knowledge_found').",
    )
    scope: QueryScope | None = Field(
        default=None,
        description="The detected query scope and intent.",
    )
    disclaimer: str = Field(
        default=_DEFAULT_MEDICAL_DISCLAIMER,
        description="Medical disclaimer safeguarding non-diagnostic intent.",
    )
    latency_ms: float | None = Field(
        default=None,
        description="Total end-to-end RAG generation latency in milliseconds.",
    )
    latencies: dict[str, float] = Field(
        default_factory=dict,
        description="Internal stage latency breakdown in milliseconds.",
    )
    request_id: str | None = Field(
        default=None,
        description="Unique correlation ID for tracing the RAG request.",
    )

