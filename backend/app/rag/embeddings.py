from typing import List
from app.llm.client import GeminiClient

class EmbeddingService:
    """Service for generating vector embeddings from text."""
    
    def __init__(self, llm_client: GeminiClient):
        self.llm_client = llm_client
        self.embedding_dimension = 768

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        embeddings = []
        for text in texts:
            # We assume GeminiClient has an embed_content or similar method, if not we simulate it
            # The exact method name depends on the existing GeminiClient implementation.
            # Assuming get_embedding(text) exists or we use gemini's embedding API.
            # Here we wrap individual calls since gemini SDK batch embedding might be implemented.
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings

    async def get_embedding(self, text: str) -> List[float]:
        """Generate an embedding for a single text."""
        # Using GeminiClient to generate embeddings
        # The specific implementation depends on the exact methods available in GeminiClient.
        # This is a placeholder for the actual embedding call.
        return await self.llm_client.get_embedding(text)
