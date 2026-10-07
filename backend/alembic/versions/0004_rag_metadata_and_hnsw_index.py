"""RAG metadata enhancement and HNSW vector index

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-06

Adds:
- Document and provenance metadata columns to ``knowledge_embeddings``:
  - ``document_id`` (VARCHAR(255), indexed)
  - ``document_title`` (VARCHAR(512))
  - ``document_version`` (VARCHAR(64))
  - ``domain`` (VARCHAR(128), indexed)
  - ``metadata`` (JSONB, default '{}'::jsonb)
  - ``embedding_model`` (VARCHAR(128))
  - ``embedding_dimension`` (INTEGER, default 768)
- HNSW vector index on ``embedding`` using cosine distance:
  ``ix_knowledge_embeddings_embedding_hnsw``
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add document grouping and provenance metadata columns
    op.add_column(
        "knowledge_embeddings",
        sa.Column("document_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "knowledge_embeddings",
        sa.Column("document_title", sa.String(512), nullable=True),
    )
    op.add_column(
        "knowledge_embeddings",
        sa.Column("document_version", sa.String(64), nullable=True),
    )
    op.add_column(
        "knowledge_embeddings",
        sa.Column("domain", sa.String(128), nullable=True),
    )
    op.add_column(
        "knowledge_embeddings",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
        ),
    )
    op.add_column(
        "knowledge_embeddings",
        sa.Column("embedding_model", sa.String(128), nullable=True),
    )
    op.add_column(
        "knowledge_embeddings",
        sa.Column(
            "embedding_dimension",
            sa.Integer(),
            server_default=sa.text("768"),
            nullable=True,
        ),
    )

    # 2. Add relational metadata indexes for targeted query filtering
    op.create_index(
        "ix_knowledge_embeddings_document_id",
        "knowledge_embeddings",
        ["document_id"],
    )
    op.create_index(
        "ix_knowledge_embeddings_domain",
        "knowledge_embeddings",
        ["domain"],
    )

    # 3. Add HNSW index on the vector embedding column for fast approximate nearest neighbor search
    op.create_index(
        "ix_knowledge_embeddings_embedding_hnsw",
        "knowledge_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    # 1. Drop vector and metadata indexes
    op.drop_index(
        "ix_knowledge_embeddings_embedding_hnsw",
        table_name="knowledge_embeddings",
    )
    op.drop_index(
        "ix_knowledge_embeddings_domain",
        table_name="knowledge_embeddings",
    )
    op.drop_index(
        "ix_knowledge_embeddings_document_id",
        table_name="knowledge_embeddings",
    )

    # 2. Drop added columns in reverse order
    op.drop_column("knowledge_embeddings", "embedding_dimension")
    op.drop_column("knowledge_embeddings", "embedding_model")
    op.drop_column("knowledge_embeddings", "metadata")
    op.drop_column("knowledge_embeddings", "domain")
    op.drop_column("knowledge_embeddings", "document_version")
    op.drop_column("knowledge_embeddings", "document_title")
    op.drop_column("knowledge_embeddings", "document_id")
