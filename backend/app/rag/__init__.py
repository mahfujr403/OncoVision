"""RAG (Retrieval-Augmented Generation) module for OncoVision.

Provides services for document ingestion, semantic chunking, embedding generation,
query scope classification, and provenance-preserving two-stage retrieval.
"""

from app.rag.classifier import (
    ClassScope,
    QueryDomain,
    QueryIntent,
    QueryScope,
    QueryScopeClassifier,
)
from app.rag.embeddings import EmbeddingService
from app.rag.generator import GroundedRAGGenerator
from app.rag.grounding import GroundingDecision, GroundingEvaluator
from app.rag.ingestion import DocumentIngestionPipeline
from app.rag.prompts import (
    GROUNDED_RAG_SYSTEM_PROMPT,
    build_grounded_user_prompt,
    format_grounded_context_sources,
)
from app.rag.retriever import (
    RAGRetriever,
    RetrievedChunk,
    RetrievedContext,
    RetrievedDocument,
)
from app.rag.safety import SafetyBoundary, SafetyEvaluation, SafetyEvaluator
from app.rag.schemas import Citation, GroundedAnswer

__all__ = [
    "ClassScope",
    "QueryDomain",
    "QueryIntent",
    "QueryScope",
    "QueryScopeClassifier",
    "EmbeddingService",
    "DocumentIngestionPipeline",
    "RAGRetriever",
    "RetrievedChunk",
    "RetrievedContext",
    "RetrievedDocument",
    "Citation",
    "GroundedAnswer",
    "SafetyBoundary",
    "SafetyEvaluation",
    "SafetyEvaluator",
    "GROUNDED_RAG_SYSTEM_PROMPT",
    "build_grounded_user_prompt",
    "format_grounded_context_sources",
    "GroundedRAGGenerator",
    "GroundingDecision",
    "GroundingEvaluator",
]
