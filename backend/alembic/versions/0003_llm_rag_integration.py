"""LLM + RAG integration: chat_messages, knowledge_embeddings, ai_summary

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-13

Adds:
- pgvector extension (CREATE EXTENSION IF NOT EXISTS vector)
- ``knowledge_embeddings`` table with a 768-dim vector column for RAG
- ``chat_messages`` table for persisting AI chat conversations
- ``ai_summary`` TEXT column on ``prediction_history`` for cached LLM summaries
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (safe to call repeatedly)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- knowledge_embeddings table ---
    op.execute("""
        CREATE TABLE knowledge_embeddings (
            id UUID PRIMARY KEY,
            content TEXT NOT NULL,
            source VARCHAR(512) NOT NULL,
            topic VARCHAR(255) NOT NULL,
            chunk_index INTEGER NOT NULL,
            embedding vector(768) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.create_index(
        "ix_knowledge_embeddings_topic",
        "knowledge_embeddings",
        ["topic"],
    )

    # --- chat_messages table ---
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prediction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prediction_history.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chat_type", sa.String(32), nullable=False),
        sa.Column("sources", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_prediction_id", "chat_messages", ["prediction_id"])
    op.create_index("ix_chat_messages_chat_type", "chat_messages", ["chat_type"])

    # --- Add ai_summary to prediction_history ---
    op.add_column(
        "prediction_history",
        sa.Column("ai_summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prediction_history", "ai_summary")
    op.drop_table("chat_messages")
    op.drop_table("knowledge_embeddings")
