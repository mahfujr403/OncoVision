"""Embedding service for RAG vector generation with worker-local caching (Phase 5.3).

Wraps the GeminiClient's ``embed`` method to provide a clean interface
for the RAG pipeline. Uses Google's ``gemini-embedding-2`` model (768 dimensions)
with bounded in-process caching for high performance and reduced API costs.
"""

from __future__ import annotations

from typing import List

from app.llm.client import GeminiClient
from app.rag.cache import QueryEmbeddingCache, get_query_embedding_cache


class EmbeddingService:
    """Service for generating vector embeddings from text with optional bounded caching."""

    EMBEDDING_DIMENSION: int = 768

    def __init__(
        self,
        llm_client: GeminiClient,
        cache: QueryEmbeddingCache | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.embedding_dimension = self.EMBEDDING_DIMENSION
        self.cache = cache if cache is not None else get_query_embedding_cache()

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts.

        Uses the GeminiClient.embed() method which calls the Gemini
        embedding API in a single batch request.
        """
        if not texts:
            return []
        embeddings = await self.llm_client.embed(texts)
        return [emb[:768] for emb in embeddings]

    async def get_embedding(self, text: str) -> List[float]:
        """Generate an embedding for a single text, utilizing query cache when available."""
        if not text or not text.strip():
            return []

        # Check in-process bounded cache
        if self.cache and self.cache.enabled:
            cached = self.cache.get(text)
            if cached is not None:
                return cached

        results = await self.llm_client.embed([text])
        if results and results[0]:
            emb = results[0][:768]
            if self.cache and self.cache.enabled and len(emb) == 768:
                self.cache.set(text, emb)
            return emb
        return []
