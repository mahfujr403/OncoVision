"""Semantic markdown chunking for OncoVision RAG (Phase 2).

Uses MarkdownHeaderTextSplitter and RecursiveCharacterTextSplitter to produce
coherent, semantic chunks within the 350-700 token boundary while generating
deterministic UUID5 chunk IDs and SHA-256 content hashes for idempotent storage.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from typing import Any

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.rag.provenance import DocumentMetadata


@dataclass
class ChunkPayload:
    """Represents an enriched, deterministic chunk ready for embedding and upsert."""

    id: uuid.UUID
    content: str
    chunk_index: int
    content_hash: str
    headers: dict[str, str]
    metadata: dict[str, Any]


class MarkdownDocumentChunker:
    """Chunks curated markdown documents using semantic heading boundaries."""

    def __init__(
        self,
        chunk_size: int = 1600,
        chunk_overlap: int = 200,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.headers_to_split_on = [
            ("#", "header_1"),
            ("##", "header_2"),
            ("###", "header_3"),
        ]
        self.md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False,
        )
        self.rec_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    @staticmethod
    def _strip_sources_section(text: str) -> str:
        """Strip trailing Sources/References section to prevent isolated link-only chunks.
        
        The extracted URLs are preserved on chunk metadata and citations.
        """
        pattern = r"\n##\s+(?:Sources|Source|References)\b.*"
        stripped = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)
        return stripped.strip()

    def chunk_document(
        self,
        content: str,
        doc_meta: DocumentMetadata,
    ) -> list[ChunkPayload]:
        """Split document into deterministic, metadata-enriched chunks."""
        clean_content = self._strip_sources_section(content)
        if not clean_content:
            clean_content = content.strip()

        # 1. Split on semantic markdown headers
        header_splits = self.md_splitter.split_text(clean_content)

        # 2. Split large sections into target token bounds (~350-700 tokens)
        raw_chunks = self.rec_splitter.split_documents(header_splits)

        chunks: list[ChunkPayload] = []
        base_meta = doc_meta.to_metadata_dict()

        for idx, doc_chunk in enumerate(raw_chunks):
            chunk_text = doc_chunk.page_content.strip()
            if not chunk_text:
                continue

            # Deterministic SHA-256 content hash
            content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:16]

            # Deterministic UUID5 primary key
            chunk_uuid = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"oncovision:{doc_meta.document_id}:{doc_meta.document_version}:{idx}",
            )

            chunk_meta = dict(base_meta)
            chunk_meta["chunk_index"] = idx
            chunk_meta["content_hash"] = content_hash
            chunk_meta["headers"] = doc_chunk.metadata

            chunks.append(
                ChunkPayload(
                    id=chunk_uuid,
                    content=chunk_text,
                    chunk_index=idx,
                    content_hash=content_hash,
                    headers=doc_chunk.metadata,
                    metadata=chunk_meta,
                )
            )

        return chunks
