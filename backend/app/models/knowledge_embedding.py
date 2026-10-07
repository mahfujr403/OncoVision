import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class KnowledgeEmbedding(Base):
    """Persisted vector chunk and metadata for RAG retrieval."""

    __tablename__ = "knowledge_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(512), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- Phase 1 Enhancement: Document & Provenance Metadata ---
    document_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    document_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    document_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    chunk_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, server_default=func.text("'{}'::jsonb")
    )
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_dimension: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=768
    )
