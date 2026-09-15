"""Embedding service for RAG vector generation (Phase 11).

Wraps the GeminiClient's ``embed`` method to provide a clean interface
for the RAG pipeline. Uses Google's ``text-embedding-004`` model via
the Gemini API.
"""

from __future__ import annotations

from typing import List

from app.llm.client import GeminiClient


class EmbeddingService:
    """Service for generating vector embeddings from text."""

    EMBEDDING_DIMENSION: int = 768

    def __init__(self, llm_client: GeminiClient) -> None:
        self.llm_client = llm_client
        self.embedding_dimension = self.EMBEDDING_DIMENSION

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts.

        Uses the GeminiClient.embed() method which calls the Gemini
        embedding API in a single batch request.
        """
        if not texts:
            return []
        return await self.llm_client.embed(texts)

    async def get_embedding(self, text: str) -> List[float]:
        """Generate an embedding for a single text."""
        results = await self.llm_client.embed([text])
        if results:
            return results[0]
        return []
