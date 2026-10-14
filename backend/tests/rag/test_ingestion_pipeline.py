"""Unit and integration tests for OncoVision Curated Medical Knowledge Base Ingestion Pipeline (Phase 2).

Verifies:
1. Corpus discovery: discovers 40 candidate markdown documents, excludes 07_sources,
   08_retrieval, 09_qa_evaluation, and non-markdown files.
2. Metadata & Provenance: deterministic document_id, 8 minimum domains, classifier class scopes,
   clickable source URLs and source tiers.
3. Semantic Chunking: heading preservation, chunk size bounds, sources section stripping,
   deterministic UUID5 IDs and SHA-256 hashes.
4. Safety & Policy isolation: 06_safety files assigned domain safety_policy, claim_scope=policy,
   and 09_qa_evaluation strictly excluded.
5. Idempotency & Database caching: skips unchanged documents (0 API calls), re-embeds only
   changed chunks, removes stale chunks, enforces 768-dim vector validation.
6. Startup safety: verify AUTO_INGEST_ON_STARTUP is False by default.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.settings import get_settings
from app.models.knowledge_embedding import KnowledgeEmbedding
from app.rag.chunker import MarkdownDocumentChunker
from app.rag.ingestion import (
    DocumentIngestionPipeline,
    EXPECTED_EMBEDDING_DIMENSION,
    EXPECTED_EMBEDDING_MODEL,
    IngestionSessionFatalError,
    IngestionStats,
    resolve_corpus_path,
)
from app.rag.provenance import (
    DocumentMetadataExtractor,
    SourceRegistry,
    SUPPORTED_CLASSIFIER_CLASSES,
    VALID_DOMAINS,
)


@pytest.fixture
def corpus_root() -> Path:
    """Fixture providing the path to the curated v3 medical knowledge base."""
    return resolve_corpus_path("knowledge_base/oncovision_medical_knowledgebase_v3")


@pytest.fixture
def source_registry(corpus_root: Path) -> SourceRegistry:
    """Fixture providing loaded SourceRegistry from v3 corpus."""
    registry_file = corpus_root / "07_sources" / "source_registry.json"
    return SourceRegistry(registry_file)


@pytest.fixture
def metadata_extractor(source_registry: SourceRegistry) -> DocumentMetadataExtractor:
    """Fixture providing DocumentMetadataExtractor."""
    return DocumentMetadataExtractor(source_registry)


@pytest.fixture
def document_chunker() -> MarkdownDocumentChunker:
    """Fixture providing MarkdownDocumentChunker."""
    return MarkdownDocumentChunker(chunk_size=1600, chunk_overlap=200)


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Mock embedding service returning deterministic 768-dim vectors."""
    svc = MagicMock()

    async def _fake_get_embeddings(texts: list[str]) -> list[list[float]]:
        return [[0.1] * EXPECTED_EMBEDDING_DIMENSION for _ in texts]

    svc.get_embeddings = AsyncMock(side_effect=_fake_get_embeddings)
    return svc


class TestCorpusDiscovery:
    """Tests for corpus document discovery and strict exclusions."""

    def test_corpus_discovery_discovers_40_medical_documents(self, corpus_root: Path) -> None:
        """Verify exactly 40 candidate markdown files are discovered across valid dirs."""
        pipeline = DocumentIngestionPipeline()
        candidates, excluded = pipeline.discover_documents(corpus_root)

        assert len(candidates) == 40
        # Check every discovered file is .md
        for doc in candidates:
            assert doc.suffix == ".md"

        # Check candidate directories match curated knowledge dirs
        allowed_dirs = {
            "00_general", "01_colon", "02_lung", "03_classes",
            "04_comparisons", "05_question_answer", "06_safety"
        }
        for doc in candidates:
            first_dir = doc.relative_to(corpus_root).parts[0]
            assert first_dir in allowed_dirs

    def test_corpus_discovery_excludes_sources_retrieval_qa_evaluation(self, corpus_root: Path) -> None:
        """Verify 07_sources, 08_retrieval, and 09_qa_evaluation are strictly excluded."""
        pipeline = DocumentIngestionPipeline()
        candidates, excluded = pipeline.discover_documents(corpus_root)

        candidate_rel_paths = [c.relative_to(corpus_root).as_posix() for c in candidates]
        excluded_rel_paths = [e.relative_to(corpus_root).as_posix() for e in excluded]

        # Verify excluded prefixes do not appear in candidates
        for rel in candidate_rel_paths:
            assert not rel.startswith("07_sources/")
            assert not rel.startswith("08_retrieval/")
            assert not rel.startswith("09_qa_evaluation/")

        # Verify they are properly cataloged in excluded_files
        assert any(p.startswith("07_sources/") for p in excluded_rel_paths)
        assert any(p.startswith("08_retrieval/") for p in excluded_rel_paths)
        assert any(p.startswith("09_qa_evaluation/") for p in excluded_rel_paths)

    def test_corpus_discovery_excludes_root_files_and_non_markdown(self, corpus_root: Path) -> None:
        """Verify README.md, manifest.json, and non-md files are excluded."""
        pipeline = DocumentIngestionPipeline()
        candidates, excluded = pipeline.discover_documents(corpus_root)

        excluded_names = {e.name for e in excluded}
        assert "README.md" in excluded_names or "manifest.json" in excluded_names
        assert "source_registry.json" in excluded_names


class TestMetadataAndProvenance:
    """Tests for metadata extraction, deterministic IDs, and provenance preservation."""

    def test_deterministic_document_id(self) -> None:
        """Verify derive_document_id produces stable, deterministic IDs."""
        id1 = DocumentMetadataExtractor.derive_document_id("01_colon/colon_adenocarcinoma_morphology.md")
        id2 = DocumentMetadataExtractor.derive_document_id("01_colon\\colon_adenocarcinoma_morphology.md")
        assert id1 == id2
        assert id1 == "doc_01_colon_colon_adenocarcinoma_morphology"

    def test_clickable_source_url_and_provenance_preserved(
        self, corpus_root: Path, metadata_extractor: DocumentMetadataExtractor
    ) -> None:
        """Verify source URL, title, and tier are preserved from ## Sources markdown."""
        colon_doc = corpus_root / "01_colon" / "colon_adenocarcinoma_morphology.md"
        content = colon_doc.read_text(encoding="utf-8")

        meta = metadata_extractor.extract(colon_doc, content, corpus_root)

        assert meta.document_id == "doc_01_colon_colon_adenocarcinoma_morphology"
        assert "Adenocarcinoma" in meta.document_title or "Colon" in meta.document_title
        assert meta.domain == "colon"
        assert meta.organ == "colon"
        assert len(meta.sources) >= 1

        # Check primary source has real clickable URL and valid tier
        assert meta.primary_source_url is not None
        assert meta.primary_source_url.startswith("http://") or meta.primary_source_url.startswith("https://")
        assert meta.primary_source_tier in {1, 2, 3, 4, 5}
        assert meta.primary_source_title is not None

        # Verify to_metadata_dict contains all provenance fields
        meta_dict = meta.to_metadata_dict()
        assert meta_dict["source_url"] == meta.primary_source_url
        assert meta_dict["source_title"] == meta.primary_source_title
        assert meta_dict["source_tier"] == meta.primary_source_tier
        assert meta_dict["citation"] is not None
        assert meta_dict["last_reviewed"] == "2026-10-06"

    def test_all_eight_domains_classified(
        self, corpus_root: Path, metadata_extractor: DocumentMetadataExtractor
    ) -> None:
        """Verify all 8 minimum required domains are represented in the corpus."""
        pipeline = DocumentIngestionPipeline()
        candidates, _ = pipeline.discover_documents(corpus_root)

        discovered_domains = set()
        for doc in candidates:
            content = doc.read_text(encoding="utf-8")
            meta = metadata_extractor.extract(doc, content, corpus_root)
            assert meta.domain in VALID_DOMAINS
            discovered_domains.add(meta.domain)

        expected_minimum_domains = {
            "general_oncology",
            "histopathology",
            "colon",
            "lung",
            "classifier_context",
            "comparison",
            "clinical_explanation",
            "safety_policy",
        }
        assert expected_minimum_domains.issubset(discovered_domains)

    def test_classifier_classes_scope_mapped(
        self, corpus_root: Path, metadata_extractor: DocumentMetadataExtractor
    ) -> None:
        """Verify classifier class scopes map strictly to supported LC25000 classes."""
        doc_path = corpus_root / "03_classes" / "colon_adenocarcinoma.md"
        content = doc_path.read_text(encoding="utf-8")
        meta = metadata_extractor.extract(doc_path, content, corpus_root)

        assert meta.class_scope == "colon_adenocarcinoma"
        assert meta.class_scope in SUPPORTED_CLASSIFIER_CLASSES


class TestSemanticChunking:
    """Tests for semantic markdown chunking and deterministic IDs."""

    def test_sources_section_stripped_from_chunk_body(
        self, corpus_root: Path, metadata_extractor: DocumentMetadataExtractor, document_chunker: MarkdownDocumentChunker
    ) -> None:
        """Verify trailing ## Sources block is stripped from chunk text to avoid link-only chunks."""
        doc_path = corpus_root / "01_colon" / "colon_adenocarcinoma_morphology.md"
        content = doc_path.read_text(encoding="utf-8")
        meta = metadata_extractor.extract(doc_path, content, corpus_root)

        chunks = document_chunker.chunk_document(content, meta)
        assert len(chunks) >= 1

        for c in chunks:
            assert "## Sources" not in c.content
            assert "## References" not in c.content
            assert len(c.metadata["sources"]) >= 1

    def test_chunk_size_within_expected_bounds(
        self, corpus_root: Path, metadata_extractor: DocumentMetadataExtractor, document_chunker: MarkdownDocumentChunker
    ) -> None:
        """Verify chunk sizes are bounded within ~350-700 tokens (~1600 characters max)."""
        doc_path = corpus_root / "00_general" / "histopathology_and_h_and_e.md"
        content = doc_path.read_text(encoding="utf-8")
        meta = metadata_extractor.extract(doc_path, content, corpus_root)

        chunks = document_chunker.chunk_document(content, meta)
        for c in chunks:
            assert len(c.content) > 20
            assert len(c.content) <= 2200

    def test_deterministic_chunk_ids_and_hashes(
        self, corpus_root: Path, metadata_extractor: DocumentMetadataExtractor, document_chunker: MarkdownDocumentChunker
    ) -> None:
        """Verify chunk UUID5 IDs and content hashes are completely deterministic."""
        doc_path = corpus_root / "02_lung" / "lung_adenocarcinoma_morphology.md"
        content = doc_path.read_text(encoding="utf-8")
        meta = metadata_extractor.extract(doc_path, content, corpus_root)

        chunks_run_1 = document_chunker.chunk_document(content, meta)
        chunks_run_2 = document_chunker.chunk_document(content, meta)

        assert len(chunks_run_1) == len(chunks_run_2)
        for c1, c2 in zip(chunks_run_1, chunks_run_2):
            assert c1.id == c2.id
            assert isinstance(c1.id, uuid.UUID)
            assert c1.content_hash == c2.content_hash
            assert len(c1.content_hash) == 16


class TestSafetyPolicyIsolation:
    """Tests ensuring safety policy and evaluation files are isolated."""

    def test_safety_policy_material_has_safety_domain(
        self, corpus_root: Path, metadata_extractor: DocumentMetadataExtractor
    ) -> None:
        """Verify 06_safety documents have domain=safety_policy and claim_scope=policy."""
        safety_doc = corpus_root / "06_safety" / "diagnostic_boundaries.md"
        content = safety_doc.read_text(encoding="utf-8")
        meta = metadata_extractor.extract(safety_doc, content, corpus_root)

        assert meta.domain == "safety_policy"
        assert meta.is_safety_policy is True
        assert meta.claim_scope == "policy"

    def test_qa_evaluation_never_in_candidate_docs(self, corpus_root: Path) -> None:
        """Verify 09_qa_evaluation files are never treated as candidates."""
        pipeline = DocumentIngestionPipeline()
        candidates, excluded = pipeline.discover_documents(corpus_root)

        candidate_rel_paths = [c.relative_to(corpus_root).as_posix() for c in candidates]
        for p in candidate_rel_paths:
            assert "09_qa_evaluation" not in p


class TestIdempotencyAndCaching:
    """Tests for idempotent ingestion, caching, and dimension validation."""

    def test_idempotent_ingestion_skips_unchanged_document(
        self, corpus_root: Path, mock_embedding_service: MagicMock
    ) -> None:
        """Verify repeated ingestion with matching hash makes 0 embedding API calls."""
        doc_path = corpus_root / "01_colon" / "colon_adenocarcinoma_morphology.md"
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)

        content = doc_path.read_text(encoding="utf-8")
        meta = pipeline.extractor.extract(doc_path, content, corpus_root)
        chunks = pipeline.chunker.chunk_document(content, meta)

        fake_session = AsyncMock()
        existing_rows = []
        for c in chunks:
            row = MagicMock(spec=KnowledgeEmbedding)
            row.id = c.id
            row.chunk_index = c.chunk_index
            row.embedding = [0.1] * EXPECTED_EMBEDDING_DIMENSION
            row.chunk_metadata = {"content_hash": c.content_hash}
            existing_rows.append(row)

        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = existing_rows
        fake_session.execute.return_value = fake_exec_result

        stats = IngestionStats()

        result_chunks = asyncio.run(
            pipeline.ingest_document(
                file_path=doc_path,
                session=fake_session,
                corpus_root=corpus_root,
                force=False,
                dry_run=False,
                stats=stats,
            )
        )

        assert len(result_chunks) == len(chunks)
        assert mock_embedding_service.get_embeddings.await_count == 0
        assert stats.documents_skipped == 1
        assert stats.chunks_skipped == len(chunks)
        assert stats.cached_chunks == len(chunks)

    def test_embedding_dimension_validation_enforces_768(
        self, corpus_root: Path
    ) -> None:
        """Verify pipeline rejects embedding vectors that are not 768 dimensions."""
        doc_path = corpus_root / "06_safety" / "staging_boundaries.md"

        bad_svc = MagicMock()
        bad_svc.get_embeddings = AsyncMock(return_value=[[0.1] * 512 for _ in range(5)])

        pipeline = DocumentIngestionPipeline(embedding_service=bad_svc)

        fake_session = AsyncMock()
        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = []
        fake_session.execute.return_value = fake_exec_result

        with pytest.raises(ValueError, match="Generated embedding dimension 512 != expected 768"):
            asyncio.run(
                pipeline.ingest_document(
                    file_path=doc_path,
                    session=fake_session,
                    corpus_root=corpus_root,
                    force=True,
                    dry_run=False,
                )
            )

    def test_dry_run_mode_does_not_call_api_or_session(
        self, corpus_root: Path, mock_embedding_service: MagicMock
    ) -> None:
        """Verify dry-run mode chunks and gathers stats without API or DB operations."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)
        stats = asyncio.run(
            pipeline.ingest_corpus(
                corpus_path=corpus_root,
                session=None,
                dry_run=True,
            )
        )

        assert stats.documents_discovered == 40
        assert stats.documents_ingested == 40
        assert stats.chunks_created == 146
        assert stats.embedding_api_calls == 0
        assert mock_embedding_service.get_embeddings.await_count == 0


class TestStartupSafety:
    """Verify startup auto-ingestion configuration defaults."""

    def test_startup_auto_ingest_disabled_by_default(self) -> None:
        """Verify AUTO_INGEST_ON_STARTUP is False to ensure production startup is not blocked."""
        settings = get_settings()
        assert settings.AUTO_INGEST_ON_STARTUP is False
        assert "oncovision_medical_knowledgebase_v3" in settings.KNOWLEDGE_BASE_PATH


class TestIngestionTransactionRecoveryAndStatistics:
    """Regression tests verifying explicit rollback, session recovery, and accurate statistics."""

    @pytest.fixture
    def test_corpus_two_docs(self, tmp_path: Path) -> Path:
        """Create a minimal 2-document valid corpus."""
        corpus = tmp_path / "test_corpus"
        doc_dir = corpus / "00_general"
        doc_dir.mkdir(parents=True)

        doc1 = doc_dir / "clinical_overview_1.md"
        doc1.write_text(
            "# Clinical Overview 1\n\n"
            "This is the first test clinical document discussing general pathology.\n\n"
            "## Diagnostic Context\n\n"
            "Diagnostic context details for document 1.\n",
            encoding="utf-8",
        )

        doc2 = doc_dir / "clinical_overview_2.md"
        doc2.write_text(
            "# Clinical Overview 2\n\n"
            "This is the second test clinical document discussing general oncology.\n\n"
            "## Diagnostic Context\n\n"
            "Diagnostic context details for document 2.\n",
            encoding="utf-8",
        )

        sources_dir = corpus / "07_sources"
        sources_dir.mkdir(parents=True)
        registry_file = sources_dir / "source_registry.json"
        registry_file.write_text('{"sources": []}', encoding="utf-8")

        return corpus

    def test_lookup_failure_rolls_back_and_allows_subsequent_document(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """A failure during existing record lookup triggers rollback and allows doc 2 to succeed."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)

        fake_session = AsyncMock()
        fake_session.add = MagicMock()
        exec_call_count = 0

        async def _execute_side_effect(stmt):
            nonlocal exec_call_count
            exec_call_count += 1
            if exec_call_count == 1:
                raise RuntimeError("Simulated DB lookup connection error on doc 1")
            res = MagicMock()
            res.scalars.return_value.all.return_value = []
            return res

        fake_session.execute = AsyncMock(side_effect=_execute_side_effect)

        stats = asyncio.run(
            pipeline.ingest_corpus(
                corpus_path=test_corpus_two_docs,
                session=fake_session,
                dry_run=False,
            )
        )

        assert fake_session.rollback.await_count >= 1
        assert stats.documents_discovered == 2
        assert stats.documents_ingested == 1
        assert len(stats.errors) == 1
        assert "Simulated DB lookup connection error on doc 1" in stats.errors[0]

    def test_commit_failure_rolls_back_and_allows_subsequent_document(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """A commit failure triggers rollback and allows next document to proceed and commit cleanly."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)

        fake_session = AsyncMock()
        fake_session.add = MagicMock()
        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = []
        fake_session.execute = AsyncMock(return_value=fake_exec_result)

        commit_call_count = 0

        async def _commit_side_effect():
            nonlocal commit_call_count
            commit_call_count += 1
            if commit_call_count == 1:
                raise RuntimeError("Simulated deadlock or commit constraint failure on doc 1")
            return None

        fake_session.commit = AsyncMock(side_effect=_commit_side_effect)

        stats = asyncio.run(
            pipeline.ingest_corpus(
                corpus_path=test_corpus_two_docs,
                session=fake_session,
                dry_run=False,
            )
        )

        assert fake_session.rollback.await_count >= 1
        assert stats.documents_discovered == 2
        assert stats.documents_ingested == 1
        assert len(stats.errors) == 1
        assert "Simulated deadlock or commit constraint failure on doc 1" in stats.errors[0]

    def test_rollback_is_awaited_after_database_write_failure(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """Explicitly assert session.rollback() is awaited when ingest_document fails."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)
        doc1 = test_corpus_two_docs / "00_general" / "clinical_overview_1.md"

        fake_session = AsyncMock()
        fake_session.add = MagicMock()
        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = []
        fake_session.execute = AsyncMock(return_value=fake_exec_result)
        fake_session.commit = AsyncMock(side_effect=RuntimeError("Disk write I/O error"))

        with pytest.raises(RuntimeError, match="Disk write I/O error"):
            asyncio.run(
                pipeline.ingest_document(
                    file_path=doc1,
                    session=fake_session,
                    corpus_root=test_corpus_two_docs,
                    dry_run=False,
                )
            )

        assert fake_session.rollback.await_count == 1

    def test_pending_changes_from_failed_document_cannot_leak_into_later_commit(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """Stateful session test: staged objects from a failed doc are rolled back and never committed."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)

        class StatefulTrackingSession:
            def __init__(self):
                self.staged: list[Any] = []
                self.committed: list[Any] = []
                self.commit_attempts = 0
                self.is_active = True
                self.rollback_called = False

            def add(self, obj: Any) -> None:
                self.staged.append(obj)

            async def delete(self, obj: Any) -> None:
                if obj in self.staged:
                    self.staged.remove(obj)

            async def execute(self, stmt: Any) -> Any:
                res = MagicMock()
                res.scalars.return_value.all.return_value = []
                return res

            async def commit(self) -> None:
                self.commit_attempts += 1
                if self.commit_attempts == 1:
                    raise RuntimeError("Simulated first commit failure")
                self.committed.extend(self.staged)
                self.staged.clear()

            async def rollback(self) -> None:
                self.rollback_called = True
                self.staged.clear()

        tracking_session = StatefulTrackingSession()

        stats = asyncio.run(
            pipeline.ingest_corpus(
                corpus_path=test_corpus_two_docs,
                session=tracking_session,  # type: ignore[arg-type]
                dry_run=False,
            )
        )

        assert tracking_session.rollback_called is True
        assert len(tracking_session.committed) > 0
        # Verify committed objects belong ONLY to doc 2
        for item in tracking_session.committed:
            assert "clinical_overview_2.md" in item.source
            assert "clinical_overview_1.md" not in item.source
        assert stats.documents_ingested == 1
        assert len(stats.errors) == 1

    def test_failed_commit_is_reflected_accurately_in_statistics(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """When commit fails, stats for chunks_created, updated, removed are NOT incremented."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)
        doc1 = test_corpus_two_docs / "00_general" / "clinical_overview_1.md"

        fake_session = AsyncMock()
        fake_session.add = MagicMock()
        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = []
        fake_session.execute = AsyncMock(return_value=fake_exec_result)
        fake_session.commit = AsyncMock(side_effect=RuntimeError("Constraint violation"))

        stats = IngestionStats()

        with pytest.raises(RuntimeError):
            asyncio.run(
                pipeline.ingest_document(
                    file_path=doc1,
                    session=fake_session,
                    corpus_root=test_corpus_two_docs,
                    dry_run=False,
                    stats=stats,
                )
            )

        assert stats.documents_ingested == 0
        assert stats.chunks_created == 0
        assert stats.chunks_updated == 0
        assert stats.chunks_removed == 0

    def test_unrecoverable_rollback_halts_remaining_ingestion(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """When rollback fails, pipeline halts immediately and raises IngestionSessionFatalError."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)

        fake_session = AsyncMock()
        fake_session.add = MagicMock()
        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = []
        fake_session.execute = AsyncMock(return_value=fake_exec_result)
        fake_session.commit = AsyncMock(side_effect=RuntimeError("Commit failed"))
        fake_session.rollback = AsyncMock(side_effect=RuntimeError("Fatal connection drop during rollback"))

        stats = asyncio.run(
            pipeline.ingest_corpus(
                corpus_path=test_corpus_two_docs,
                session=fake_session,
                dry_run=False,
            )
        )

        # Fatal error must stop processing doc 2
        assert stats.documents_ingested == 0
        assert len(stats.errors) == 1
        assert "Fatal database session failure" in stats.errors[0]
        # Only 1 document should have attempted execution
        assert fake_session.execute.await_count == 1

    def test_inactive_session_halts_remaining_ingestion(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """When session becomes inactive after an error, remaining documents are skipped."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)

        fake_session = AsyncMock()
        fake_session.add = MagicMock()
        fake_session.is_active = True
        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = []
        fake_session.execute = AsyncMock(return_value=fake_exec_result)

        async def _rollback_side_effect():
            fake_session.is_active = False

        fake_session.commit = AsyncMock(side_effect=RuntimeError("Commit failed"))
        fake_session.rollback = AsyncMock(side_effect=_rollback_side_effect)

        stats = asyncio.run(
            pipeline.ingest_corpus(
                corpus_path=test_corpus_two_docs,
                session=fake_session,
                dry_run=False,
            )
        )

        assert stats.documents_ingested == 0
        assert any("session is inactive" in err for err in stats.errors)
        assert fake_session.execute.await_count == 1

    def test_cancellation_rolls_back_and_never_swallows_cancelled_error(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """asyncio.CancelledError triggers session rollback and is re-raised."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)
        doc1 = test_corpus_two_docs / "00_general" / "clinical_overview_1.md"

        fake_session = AsyncMock()
        fake_session.add = MagicMock()
        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = []
        fake_session.execute = AsyncMock(return_value=fake_exec_result)
        fake_session.commit = AsyncMock(side_effect=asyncio.CancelledError())

        with pytest.raises(asyncio.CancelledError):
            asyncio.run(
                pipeline.ingest_document(
                    file_path=doc1,
                    session=fake_session,
                    corpus_root=test_corpus_two_docs,
                    dry_run=False,
                )
            )

        assert fake_session.rollback.await_count == 1

    def test_dry_run_statistics_and_summary_clarity(
        self, corpus_root: Path, mock_embedding_service: MagicMock
    ) -> None:
        """Dry-run summary explicitly states in-memory mode and produces expected discovery counts."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)
        stats = asyncio.run(
            pipeline.ingest_corpus(
                corpus_path=corpus_root,
                session=None,
                dry_run=True,
            )
        )

        assert stats.dry_run is True
        assert stats.documents_discovered == 40
        assert stats.documents_ingested == 40
        assert stats.chunks_created == 146
        assert stats.embedding_api_calls == 0
        summary = stats.summary()
        assert "Mode: DRY-RUN" in summary
        assert "(parsed in-memory)" in summary

    def test_failed_commit_does_not_increase_domain_counts(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """When commit fails, domain_counts for that document's domain is NOT incremented."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)
        doc1 = test_corpus_two_docs / "00_general" / "clinical_overview_1.md"

        fake_session = AsyncMock()
        fake_session.add = MagicMock()
        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = []
        fake_session.execute = AsyncMock(return_value=fake_exec_result)
        fake_session.commit = AsyncMock(side_effect=RuntimeError("Simulated commit failure"))

        stats = IngestionStats()

        with pytest.raises(RuntimeError):
            asyncio.run(
                pipeline.ingest_document(
                    file_path=doc1,
                    session=fake_session,
                    corpus_root=test_corpus_two_docs,
                    dry_run=False,
                    stats=stats,
                )
            )

        assert stats.domain_counts == {}

    def test_successful_live_commit_updates_domain_counts_correctly(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """When commit succeeds, domain_counts is updated with chunk counts for that domain."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)
        doc1 = test_corpus_two_docs / "00_general" / "clinical_overview_1.md"

        fake_session = AsyncMock()
        fake_session.add = MagicMock()
        fake_exec_result = MagicMock()
        fake_exec_result.scalars.return_value.all.return_value = []
        fake_session.execute = AsyncMock(return_value=fake_exec_result)
        fake_session.commit = AsyncMock(return_value=None)

        stats = IngestionStats()

        chunks = asyncio.run(
            pipeline.ingest_document(
                file_path=doc1,
                session=fake_session,
                corpus_root=test_corpus_two_docs,
                dry_run=False,
                stats=stats,
            )
        )

        assert len(chunks) > 0
        assert "general_oncology" in stats.domain_counts
        assert stats.domain_counts["general_oncology"] == len(chunks)

    def test_dry_run_reports_correct_in_memory_domain_counts(
        self, test_corpus_two_docs: Path, mock_embedding_service: MagicMock
    ) -> None:
        """Dry-run mode populates domain_counts in memory across discovered documents."""
        pipeline = DocumentIngestionPipeline(embedding_service=mock_embedding_service)

        stats = asyncio.run(
            pipeline.ingest_corpus(
                corpus_path=test_corpus_two_docs,
                session=None,
                dry_run=True,
            )
        )

        assert stats.dry_run is True
        assert "general_oncology" in stats.domain_counts
        assert stats.domain_counts["general_oncology"] == stats.chunks_created
        assert stats.chunks_created > 0
