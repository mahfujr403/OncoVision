"""Unit and schema tests for KnowledgeEmbedding and Alembic migration 0004 (Phase 1).

Verifies:
1. KnowledgeEmbedding model imports correctly and matches expected table structure.
2. New fields (document_id, document_title, document_version, domain, metadata,
   embedding_model, embedding_dimension) are represented correctly.
3. Existing knowledge records remain fully backward compatible.
4. pgvector column remains 768-dimensional.
5. HNSW vector index definition and Alembic revision chain.
6. Migration downgrade does not destroy unrelated tables or base columns.
"""

import uuid
from typing import Any

import pytest
from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.knowledge_embedding import KnowledgeEmbedding


class TestKnowledgeEmbeddingModel:
    """Tests for the KnowledgeEmbedding SQLAlchemy ORM model."""

    def test_knowledge_embedding_imports_and_table_name(self) -> None:
        """Verify model imports cleanly and maps to the correct table."""
        assert KnowledgeEmbedding.__tablename__ == "knowledge_embeddings"
        columns = KnowledgeEmbedding.__table__.columns

        # Verify baseline columns
        assert "id" in columns
        assert "content" in columns
        assert "source" in columns
        assert "topic" in columns
        assert "chunk_index" in columns
        assert "embedding" in columns
        assert "created_at" in columns

        # Verify Phase 1 enhancement columns
        assert "document_id" in columns
        assert "document_title" in columns
        assert "document_version" in columns
        assert "domain" in columns
        assert "metadata" in columns
        assert "embedding_model" in columns
        assert "embedding_dimension" in columns

    def test_new_fields_represented_correctly(self) -> None:
        """Verify column types and nullability for Phase 1 metadata columns."""
        table = KnowledgeEmbedding.__table__

        doc_id_col = table.c.document_id
        assert isinstance(doc_id_col.type, String)
        assert doc_id_col.type.length == 255
        assert doc_id_col.nullable is True

        title_col = table.c.document_title
        assert isinstance(title_col.type, String)
        assert title_col.type.length == 512
        assert title_col.nullable is True

        version_col = table.c.document_version
        assert isinstance(version_col.type, String)
        assert version_col.type.length == 64
        assert version_col.nullable is True

        domain_col = table.c.domain
        assert isinstance(domain_col.type, String)
        assert domain_col.type.length == 128
        assert domain_col.nullable is True

        metadata_col = table.c.metadata
        assert isinstance(metadata_col.type, JSONB)
        assert metadata_col.nullable is True

        model_col = table.c.embedding_model
        assert isinstance(model_col.type, String)
        assert model_col.type.length == 128
        assert model_col.nullable is True

        dim_col = table.c.embedding_dimension
        assert isinstance(dim_col.type, Integer)
        assert dim_col.nullable is True

    def test_pgvector_dimension_is_768(self) -> None:
        """Verify the pgvector embedding column maintains exact 768 dimensionality."""
        table = KnowledgeEmbedding.__table__
        embedding_col = table.c.embedding
        assert isinstance(embedding_col.type, Vector)
        assert embedding_col.type.dim == 768

    def test_backward_compatibility_with_legacy_constructor(self) -> None:
        """Verify instantiating with only legacy fields succeeds without error."""
        legacy_embedding = [0.01] * 768
        record = KnowledgeEmbedding(
            content="Normal colonic mucosa consists of straight tubular crypts.",
            source="colon_cancer/overview.md",
            topic="colon_cancer",
            chunk_index=0,
            embedding=legacy_embedding,
        )

        assert record.content == "Normal colonic mucosa consists of straight tubular crypts."
        assert record.source == "colon_cancer/overview.md"
        assert record.topic == "colon_cancer"
        assert record.chunk_index == 0
        assert len(record.embedding) == 768
        # Newly added fields default gracefully
        assert record.document_id is None
        assert record.document_title is None
        assert record.document_version is None
        assert record.domain is None
        assert record.chunk_metadata is None or record.chunk_metadata == {}
        assert record.embedding_model is None
        assert record.embedding_dimension is None or record.embedding_dimension == 768

    def test_full_instantiation_with_phase_1_metadata(self) -> None:
        """Verify instantiating with full provenance metadata sets all attributes."""
        record_id = uuid.uuid4()
        vector_data = [0.05] * 768
        meta_dict = {
            "author": "World Health Organization",
            "year": 2024,
            "doi": "10.1016/sample.doi",
            "evidence_level": "Level I",
        }

        record = KnowledgeEmbedding(
            id=record_id,
            content="Glandular cribriform architecture indicative of adenocarcinoma.",
            source="colon_cancer/adenocarcinoma.md",
            topic="colon_cancer",
            chunk_index=1,
            embedding=vector_data,
            document_id="doc-colon-adeno-v1",
            document_title="Pathology and Genetics of Tumours of the Digestive System",
            document_version="1.0.0",
            domain="histopathology",
            chunk_metadata=meta_dict,
            embedding_model="gemini-embedding-2",
            embedding_dimension=768,
        )

        assert record.id == record_id
        assert record.document_id == "doc-colon-adeno-v1"
        assert record.document_title == "Pathology and Genetics of Tumours of the Digestive System"
        assert record.document_version == "1.0.0"
        assert record.domain == "histopathology"
        assert record.chunk_metadata == meta_dict
        assert record.embedding_model == "gemini-embedding-2"
        assert record.embedding_dimension == 768


class TestAlembicMigration0004:
    """Tests for Alembic revision chain and migration 0004 operations."""

    def test_alembic_revision_chain(self) -> None:
        """Verify revision 0004 is the single current head and links to 0003."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(cfg)

        heads = script.get_heads()
        assert heads == ["0004"]

        rev_0004 = script.get_revision("0004")
        assert rev_0004 is not None
        assert rev_0004.down_revision == "0003"
        assert "HNSW" in rev_0004.doc or "metadata" in rev_0004.doc

    def test_migration_0004_sql_execution(self, capsys: pytest.CaptureFixture) -> None:
        """Verify offline SQL generation for migration 0004 upgrade and downgrade."""
        from alembic.config import Config
        from alembic import command

        cfg = Config("alembic.ini")

        # Run offline SQL generation for upgrade from 0003 to 0004
        command.upgrade(cfg, "0003:0004", sql=True)
        upgrade_captured = capsys.readouterr()
        upgrade_sql = upgrade_captured.out

        # Assert upgrade statements
        assert "ALTER TABLE knowledge_embeddings ADD COLUMN document_id" in upgrade_sql
        assert "ALTER TABLE knowledge_embeddings ADD COLUMN document_title" in upgrade_sql
        assert "ALTER TABLE knowledge_embeddings ADD COLUMN domain" in upgrade_sql
        assert "ALTER TABLE knowledge_embeddings ADD COLUMN metadata JSONB" in upgrade_sql
        assert "ALTER TABLE knowledge_embeddings ADD COLUMN embedding_model" in upgrade_sql
        assert "ALTER TABLE knowledge_embeddings ADD COLUMN embedding_dimension" in upgrade_sql
        assert "CREATE INDEX ix_knowledge_embeddings_document_id" in upgrade_sql
        assert "CREATE INDEX ix_knowledge_embeddings_domain" in upgrade_sql
        assert "CREATE INDEX ix_knowledge_embeddings_embedding_hnsw ON knowledge_embeddings USING hnsw (embedding vector_cosine_ops)" in upgrade_sql

        # Run offline SQL generation for downgrade from 0004 to 0003
        command.downgrade(cfg, "0004:0003", sql=True)
        downgrade_captured = capsys.readouterr()
        downgrade_sql = downgrade_captured.out

        # Assert downgrade statements drop only added elements
        assert "DROP INDEX ix_knowledge_embeddings_embedding_hnsw" in downgrade_sql
        assert "DROP INDEX ix_knowledge_embeddings_domain" in downgrade_sql
        assert "DROP INDEX ix_knowledge_embeddings_document_id" in downgrade_sql
        assert "ALTER TABLE knowledge_embeddings DROP COLUMN document_id" in downgrade_sql
        assert "ALTER TABLE knowledge_embeddings DROP COLUMN metadata" in downgrade_sql
        assert "ALTER TABLE knowledge_embeddings DROP COLUMN embedding_dimension" in downgrade_sql
        # Assert table itself is NOT dropped
        assert "DROP TABLE knowledge_embeddings" not in downgrade_sql
        assert "DROP TABLE chat_messages" not in downgrade_sql
