"""Curated Medical Knowledge Base Ingestion Pipeline (Phase 2).

Provides safe, deterministic, provenance-preserving, and idempotent ingestion
of the OncoVision curated medical knowledge base into PostgreSQL with pgvector.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.models.knowledge_embedding import KnowledgeEmbedding
from app.rag.chunker import ChunkPayload, MarkdownDocumentChunker
from app.rag.embeddings import EmbeddingService
from app.rag.provenance import (
    DocumentMetadata,
    DocumentMetadataExtractor,
    SourceRegistry,
    VALID_DOMAINS,
)

logger = logging.getLogger(__name__)

# Fixed embedding specifications (Phase 1 & 2 contract)
EXPECTED_EMBEDDING_MODEL = "gemini-embedding-2"
EXPECTED_EMBEDDING_DIMENSION = 768

# Directories strictly excluded from production vector retrieval index
EXCLUDED_DIRECTORIES = {
    "07_sources",        # Source registry and bibliography only
    "08_retrieval",      # Engineering and architecture guidance
    "09_qa_evaluation",  # Test questions, benchmark rubrics, eval datasets
}

# Standard curated v3 directory prefixes
INCLUDED_V3_DIRECTORIES = {
    "00_general",
    "01_colon",
    "02_lung",
    "03_classes",
    "04_comparisons",
    "05_question_answer",
    "06_safety",
}


def resolve_corpus_path(configured_path: str | Path | None = None) -> Path:
    """Resolve knowledge base directory across Windows dev, Docker, and relative runs."""
    settings = get_settings()
    raw_path_str = str(configured_path or settings.KNOWLEDGE_BASE_PATH)
    raw_path = Path(raw_path_str)

    if raw_path.is_absolute() and raw_path.exists():
        return raw_path

    # Candidate roots based on working directory and module location
    candidates = [
        raw_path,
        Path.cwd() / raw_path,
        Path.cwd().parent / raw_path,
        Path(__file__).resolve().parents[3] / raw_path,  # Repo root / path
        Path(__file__).resolve().parents[2] / raw_path,  # Backend / path
    ]
    for cand in candidates:
        if cand.exists() and cand.is_dir():
            return cand.resolve()

    raise FileNotFoundError(
        f"Could not locate knowledge base directory at '{raw_path_str}'. "
        f"Checked candidate locations: {[str(c) for c in candidates]}"
    )


@dataclass
class IngestionStats:
    """Detailed metrics tracking for an ingestion run."""

    documents_discovered: int = 0
    documents_ingested: int = 0
    documents_skipped: int = 0
    documents_excluded: int = 0
    chunks_created: int = 0
    chunks_skipped: int = 0
    chunks_updated: int = 0
    chunks_removed: int = 0
    embedding_api_calls: int = 0
    cached_chunks: int = 0
    domain_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Format a human-readable execution summary."""
        domain_lines = [
            f"  - {d}: {cnt}" for d, cnt in sorted(self.domain_counts.items())
        ]
        domain_str = "\n".join(domain_lines) if domain_lines else "  None"
        error_str = f"\nErrors ({len(self.errors)}):\n" + "\n".join(f"  ! {e}" for e in self.errors) if self.errors else ""

        return (
            f"==================================================\n"
            f"OncoVision KB Ingestion Pipeline Execution Summary\n"
            f"==================================================\n"
            f"Documents:\n"
            f"  Discovered: {self.documents_discovered}\n"
            f"  Ingested:   {self.documents_ingested}\n"
            f"  Skipped:    {self.documents_skipped} (unchanged / hash matched)\n"
            f"  Excluded:   {self.documents_excluded} (sources, retrieval, qa_eval, non-md)\n"
            f"Chunks:\n"
            f"  Created:    {self.chunks_created}\n"
            f"  Updated:    {self.chunks_updated}\n"
            f"  Skipped:    {self.chunks_skipped} (identical content hash)\n"
            f"  Removed:    {self.chunks_removed} (stale)\n"
            f"Embeddings:\n"
            f"  Model:      {EXPECTED_EMBEDDING_MODEL}\n"
            f"  Dimension:  {EXPECTED_EMBEDDING_DIMENSION}\n"
            f"  API Calls:  {self.embedding_api_calls}\n"
            f"  Cached:     {self.cached_chunks}\n"
            f"Domain Distribution (chunks):\n"
            f"{domain_str}\n"
            f"=================================================="
            f"{error_str}"
        )


class DocumentIngestionPipeline:
    """Robust, idempotent pipeline for ingesting curated medical knowledge."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        registry_file: Path | None = None,
        chunk_size: int = 1600,
        chunk_overlap: int = 200,
    ) -> None:
        self.embedding_service = embedding_service
        self.registry = SourceRegistry(registry_file)
        self.extractor = DocumentMetadataExtractor(self.registry)
        self.chunker = MarkdownDocumentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def discover_documents(
        self, corpus_path: Path
    ) -> tuple[list[Path], list[Path]]:
        """Discover valid knowledge base documents and identify excluded items."""
        candidate_docs: list[Path] = []
        excluded_files: list[Path] = []

        for root, _, files in os.walk(corpus_path):
            root_path = Path(root)
            rel_root = root_path.relative_to(corpus_path).as_posix()
            first_dir = rel_root.split("/")[0] if rel_root != "." else ""

            # Check if this entire directory subtree is excluded
            if first_dir in EXCLUDED_DIRECTORIES:
                for f in files:
                    excluded_files.append(root_path / f)
                continue

            for file in sorted(files):
                file_path = root_path / file
                # Skip non-markdown files
                if not (file.endswith(".md") or file.endswith(".txt")):
                    excluded_files.append(file_path)
                    continue

                # Skip root-level summary/manifest files
                if rel_root == "." and file in {"README.md", "manifest.json", "CORPUS_STATS.json"}:
                    excluded_files.append(file_path)
                    continue

                candidate_docs.append(file_path)

        return sorted(candidate_docs), sorted(excluded_files)

    async def ingest_document(
        self,
        file_path: Path,
        session: AsyncSession | None = None,
        corpus_root: Path | None = None,
        force: bool = False,
        dry_run: bool = False,
        stats: IngestionStats | None = None,
    ) -> list[ChunkPayload]:
        """Ingest a single document safely, preserving provenance and enforcing idempotency."""
        if not file_path.exists():
            msg = f"Document not found: {file_path}"
            logger.error(msg)
            if stats:
                stats.errors.append(msg)
            return []

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            msg = f"Failed to read {file_path}: {e}"
            logger.error(msg)
            if stats:
                stats.errors.append(msg)
            return []

        if not content.strip():
            msg = f"Empty content in {file_path}, skipping."
            logger.warning(msg)
            if stats:
                stats.errors.append(msg)
            return []

        # Determine effective corpus root for relative paths
        if corpus_root is None:
            corpus_root = file_path.parent.parent

        # 1. Metadata and provenance extraction
        doc_meta = self.extractor.extract(file_path, content, corpus_root)

        # 2. Semantic markdown chunking
        chunks = self.chunker.chunk_document(content, doc_meta)
        if not chunks:
            logger.warning("No chunks generated for %s", file_path)
            return []

        if stats:
            stats.domain_counts[doc_meta.domain] = (
                stats.domain_counts.get(doc_meta.domain, 0) + len(chunks)
            )

        if dry_run or session is None:
            if stats:
                stats.documents_ingested += 1
                stats.chunks_created += len(chunks)
            return chunks

        # 3. Idempotency Check: Examine existing records for this document
        stmt = (
            select(KnowledgeEmbedding)
            .where(KnowledgeEmbedding.document_id == doc_meta.document_id)
            .order_by(KnowledgeEmbedding.chunk_index)
        )
        result = await session.execute(stmt)
        existing_rows = list(result.scalars().all())

        is_unchanged = False
        if not force and len(existing_rows) == len(chunks):
            all_hashes_match = True
            for row, chunk in zip(existing_rows, chunks):
                row_hash = (row.chunk_metadata or {}).get("content_hash")
                if row_hash != chunk.content_hash:
                    all_hashes_match = False
                    break
            if all_hashes_match:
                is_unchanged = True

        if is_unchanged:
            logger.debug("Document %s is unchanged. Skipping embedding generation.", doc_meta.document_id)
            if stats:
                stats.documents_skipped += 1
                stats.chunks_skipped += len(chunks)
                stats.cached_chunks += len(chunks)
            return chunks

        # 4. Generate Embeddings (caching unchanged chunks where applicable)
        existing_embeddings_by_hash: dict[str, list[float]] = {}
        for row in existing_rows:
            r_hash = (row.chunk_metadata or {}).get("content_hash")
            if (
                r_hash
                and row.embedding is not None
                and len(row.embedding) == EXPECTED_EMBEDDING_DIMENSION
            ):
                existing_embeddings_by_hash[r_hash] = row.embedding

        chunks_to_embed: list[tuple[int, str]] = []
        final_embeddings: list[list[float]] = [[] for _ in chunks]

        for i, chunk in enumerate(chunks):
            if not force and chunk.content_hash in existing_embeddings_by_hash:
                final_embeddings[i] = existing_embeddings_by_hash[chunk.content_hash]
                if stats:
                    stats.cached_chunks += 1
            else:
                chunks_to_embed.append((i, chunk.content))

        if chunks_to_embed:
            if not self.embedding_service:
                raise RuntimeError(
                    f"EmbeddingService is required to embed {len(chunks_to_embed)} new chunks "
                    f"for document {doc_meta.document_id}."
                )
            texts = [text for _, text in chunks_to_embed]
            new_embeddings = await self.embedding_service.get_embeddings(texts)
            if stats:
                stats.embedding_api_calls += 1

            for (idx, _), emb in zip(chunks_to_embed, new_embeddings):
                if len(emb) != EXPECTED_EMBEDDING_DIMENSION:
                    raise ValueError(
                        f"Generated embedding dimension {len(emb)} != expected {EXPECTED_EMBEDDING_DIMENSION}"
                    )
                final_embeddings[idx] = emb

        # 5. Database Upsert and Stale Chunk Removal
        new_chunk_ids = {c.id for c in chunks}
        stale_rows = [r for r in existing_rows if r.id not in new_chunk_ids]
        for stale_row in stale_rows:
            await session.delete(stale_row)
            if stats:
                stats.chunks_removed += 1

        existing_rows_by_id = {r.id: r for r in existing_rows}

        for chunk, emb in zip(chunks, final_embeddings):
            if chunk.id in existing_rows_by_id:
                row = existing_rows_by_id[chunk.id]
                row.content = chunk.content
                row.source = doc_meta.relative_path
                row.topic = doc_meta.domain
                row.chunk_index = chunk.chunk_index
                row.embedding = emb
                row.document_id = doc_meta.document_id
                row.document_title = doc_meta.document_title
                row.document_version = doc_meta.document_version
                row.domain = doc_meta.domain
                row.chunk_metadata = chunk.metadata
                row.embedding_model = EXPECTED_EMBEDDING_MODEL
                row.embedding_dimension = EXPECTED_EMBEDDING_DIMENSION
                if stats:
                    stats.chunks_updated += 1
            else:
                new_record = KnowledgeEmbedding(
                    id=chunk.id,
                    content=chunk.content,
                    source=doc_meta.relative_path,
                    topic=doc_meta.domain,
                    chunk_index=chunk.chunk_index,
                    embedding=emb,
                    document_id=doc_meta.document_id,
                    document_title=doc_meta.document_title,
                    document_version=doc_meta.document_version,
                    domain=doc_meta.domain,
                    chunk_metadata=chunk.metadata,
                    embedding_model=EXPECTED_EMBEDDING_MODEL,
                    embedding_dimension=EXPECTED_EMBEDDING_DIMENSION,
                )
                session.add(new_record)
                if stats:
                    stats.chunks_created += 1

        await session.commit()
        if stats:
            stats.documents_ingested += 1

        return chunks

    async def ingest_corpus(
        self,
        corpus_path: Path,
        session: AsyncSession | None = None,
        force: bool = False,
        dry_run: bool = False,
        target_document: str | None = None,
    ) -> IngestionStats:
        """Ingest the complete knowledge base corpus with statistics and error resilience."""
        stats = IngestionStats()

        # Update registry if source_registry.json exists in corpus
        registry_file = corpus_path / "07_sources" / "source_registry.json"
        if registry_file.exists():
            self.registry = SourceRegistry(registry_file)
            self.extractor = DocumentMetadataExtractor(self.registry)

        candidate_docs, excluded_files = self.discover_documents(corpus_path)
        stats.documents_discovered = len(candidate_docs)
        stats.documents_excluded = len(excluded_files)

        if target_document:
            norm_target = target_document.replace("\\", "/").lower()
            filtered_docs = [
                doc for doc in candidate_docs
                if norm_target in str(doc).replace("\\", "/").lower()
            ]
            if not filtered_docs:
                msg = f"Target document filter '{target_document}' matched 0 discovered documents."
                logger.error(msg)
                stats.errors.append(msg)
                return stats
            candidate_docs = filtered_docs
            logger.info("Filtered ingestion to %d target document(s).", len(candidate_docs))

        for file_path in candidate_docs:
            try:
                await self.ingest_document(
                    file_path=file_path,
                    session=session,
                    corpus_root=corpus_path,
                    force=force,
                    dry_run=dry_run,
                    stats=stats,
                )
            except Exception as e:
                msg = f"Error ingesting document {file_path.name}: {e}"
                logger.error(msg, exc_info=True)
                stats.errors.append(msg)

        return stats

    # Backward-compatible helpers
    async def ingest_directory(
        self,
        directory: Path,
        session: AsyncSession | None,
        force: bool = False,
        dry_run: bool = False,
    ) -> IngestionStats:
        """Ingest all valid documents in a directory (backward-compatible method)."""
        return await self.ingest_corpus(
            corpus_path=directory,
            session=session,
            force=force,
            dry_run=dry_run,
        )

    async def clear_and_reingest(
        self,
        directory: Path,
        session: AsyncSession,
        dry_run: bool = False,
    ) -> IngestionStats:
        """Clear all existing embeddings and reingest directory from scratch."""
        if not dry_run:
            await session.execute(delete(KnowledgeEmbedding))
            await session.commit()
        return await self.ingest_corpus(
            corpus_path=directory,
            session=session,
            force=True,
            dry_run=dry_run,
        )


async def run_cli() -> None:
    """CLI runner for knowledge base ingestion."""
    parser = argparse.ArgumentParser(
        description="OncoVision Curated Medical Knowledge Base Ingestion CLI (Phase 2)"
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to curated knowledge base directory (defaults to settings.KNOWLEDGE_BASE_PATH)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate, chunk, and report without generating embeddings or writing to database",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-generation of embeddings even if content hashes match",
    )
    parser.add_argument(
        "--document",
        type=str,
        default=None,
        help="Ingest a specific document only (matches filename or relative path substring)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing embeddings before ingestion",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    corpus_path = resolve_corpus_path(args.path)
    logger.info("Resolved knowledge base corpus path: %s", corpus_path)

    settings = get_settings()

    if args.dry_run:
        logger.info("Running in DRY-RUN mode (no API calls, no database mutations)...")
        pipeline = DocumentIngestionPipeline()
        stats = await pipeline.ingest_corpus(
            corpus_path=corpus_path,
            session=None,
            force=args.force,
            dry_run=True,
            target_document=args.document,
        )
        print("\n" + stats.summary() + "\n")
        return

    # Database and Embedding Service connection
    if not settings.GOOGLE_API_KEY:
        print("\n[ERROR] GOOGLE_API_KEY is required to generate embeddings. Set it in environment or .env.\n")
        sys.exit(1)

    from app.database.session import AsyncSessionLocal
    from app.llm.client import get_gemini_client

    llm_client = get_gemini_client(settings.GOOGLE_API_KEY, settings.LLM_MODEL)
    embedding_service = EmbeddingService(llm_client)
    pipeline = DocumentIngestionPipeline(embedding_service=embedding_service)

    async with AsyncSessionLocal() as session:
        if args.clear:
            logger.info("Clearing all existing knowledge embeddings...")
            await session.execute(delete(KnowledgeEmbedding))
            await session.commit()

        stats = await pipeline.ingest_corpus(
            corpus_path=corpus_path,
            session=session,
            force=args.force,
            dry_run=False,
            target_document=args.document,
        )

    print("\n" + stats.summary() + "\n")
    if stats.errors:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_cli())
