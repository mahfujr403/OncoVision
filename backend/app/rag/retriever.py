from typing import List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.rag.embeddings import EmbeddingService
from app.models.knowledge_embedding import KnowledgeEmbedding

import logging

logger = logging.getLogger(__name__)


class RetrievedDocument(BaseModel):
    content: str
    source: str
    topic: str
    similarity: float


class RAGRetriever:
    """Retrieval service for the RAG pipeline."""

    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService):
        self.session = session
        self.embedding_service = embedding_service

    async def retrieve(self, query: str, top_k: int = 5, similarity_threshold: float = 0.7) -> List[RetrievedDocument]:
        """Retrieve relevant documents based on semantic similarity."""
        try:
            # Check if there are any documents before making a remote embedding API call
            has_records = await self.session.scalar(select(KnowledgeEmbedding.id).limit(1))
            if has_records is None:
                return []

            query_embedding = await self.embedding_service.get_embedding(query)
            if not query_embedding:
                logger.warning("Empty embedding returned for query '%s'", query[:50])
                return []

            # pgvector cosine distance operator is `<=>`
            # cosine similarity = 1 - cosine distance
            distance_expr = KnowledgeEmbedding.embedding.cosine_distance(query_embedding)
            similarity_expr = (1.0 - distance_expr).label("similarity")

            stmt = (
                select(KnowledgeEmbedding, similarity_expr)
                .where(similarity_expr >= similarity_threshold)
                .order_by(distance_expr)
                .limit(top_k)
            )

            result = await self.session.execute(stmt)
            rows = result.all()

            documents = []
            for row in rows:
                embedding_record = row[0]
                similarity = row.similarity
                documents.append(
                    RetrievedDocument(
                        content=embedding_record.content,
                        source=embedding_record.source,
                        topic=embedding_record.topic,
                        similarity=float(similarity),
                    )
                )

            return documents
        except Exception as e:
            logger.warning("RAG retrieval failed gracefully: %s", e)
            try:
                await self.session.rollback()
            except Exception:
                pass
            return []

    def format_context(self, documents: List[RetrievedDocument]) -> str:
        """Format retrieved documents into a context string."""
        if not documents:
            return "No relevant context found."
            
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(
                f"[Document {i}] (Source: {doc.source}, Topic: {doc.topic})\n{doc.content}"
            )
            
        return "\n\n".join(context_parts)
