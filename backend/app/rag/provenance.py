"""Provenance and document metadata extraction for OncoVision RAG (Phase 2).

Preserves authoritative bibliographic provenance (NCI, CAP, NCBI, PMC),
determines semantic domains, maps classifier class scopes, and extracts
structured sources from curated knowledge base documents.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Canonical classifier classes from OncoVision Model Manifest
SUPPORTED_CLASSIFIER_CLASSES: set[str] = {
    "colon_adenocarcinoma",
    "benign_colonic_tissue",
    "lung_adenocarcinoma",
    "benign_lung_tissue",
    "lung_squamous_cell_carcinoma",
}

# Minimum supported knowledge domains
VALID_DOMAINS: set[str] = {
    "general_oncology",
    "histopathology",
    "colon",
    "lung",
    "classifier_context",
    "comparison",
    "clinical_explanation",
    "safety_policy",
    "developer_info",
    "platform_info",
}


@dataclass(frozen=True)
class SourceEntry:
    """Entry in the master source registry."""

    title: str
    url: str
    tier: int


class SourceRegistry:
    """Registry of verified medical knowledge sources and hierarchy tiers."""

    def __init__(self, registry_file: Path | None = None) -> None:
        self._sources_by_url: dict[str, SourceEntry] = {}
        self._sources_by_title: dict[str, SourceEntry] = {}

        if registry_file and registry_file.exists():
            try:
                data = json.loads(registry_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "url" in item and "title" in item:
                            entry = SourceEntry(
                                title=str(item["title"]).strip(),
                                url=str(item["url"]).strip(),
                                tier=int(item.get("tier", 3)),
                            )
                            self._sources_by_url[entry.url.lower().rstrip("/")] = entry
                            self._sources_by_title[entry.title.lower()] = entry
                logger.info("Loaded %d sources into SourceRegistry.", len(self._sources_by_url))
            except Exception as e:
                logger.warning("Failed to load source registry from %s: %s", registry_file, e)

    def resolve(self, url: str, fallback_title: str | None = None) -> SourceEntry:
        """Resolve or synthesize a SourceEntry with appropriate priority tier."""
        clean_url = url.strip().rstrip("/")
        norm_url = clean_url.lower()

        if norm_url in self._sources_by_url:
            return self._sources_by_url[norm_url]

        # Tier heuristic based on authoritative institutional domains
        title = fallback_title or "Clinical Evidence Source"
        if "cancer.gov" in norm_url or "cap.org" in norm_url:
            tier = 1
        elif "ncbi.nlm.nih.gov/books" in norm_url or "statpearls" in norm_url:
            tier = 2
        elif "ncbi.nlm.nih.gov" in norm_url or "pmc" in norm_url:
            tier = 3
        elif "openstax.org" in norm_url:
            tier = 4
        elif "arxiv.org" in norm_url or "github.com" in norm_url:
            tier = 5
        else:
            tier = 3

        return SourceEntry(title=title, url=clean_url, tier=tier)


@dataclass
class DocumentMetadata:
    """Rich provenance and domain metadata for a curated knowledge document."""

    document_id: str
    document_title: str
    document_version: str
    domain: str
    relative_path: str
    organ: str
    class_scope: str | list[str] | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)
    primary_source_title: str | None = None
    primary_source_url: str | None = None
    primary_source_tier: int | None = None
    last_reviewed: str = "2026-10-06"
    is_safety_policy: bool = False
    claim_scope: str = "educational"

    def to_metadata_dict(self) -> dict[str, Any]:
        """Convert to JSONB-compatible dictionary for KnowledgeEmbedding.metadata."""
        return {
            "document_id": self.document_id,
            "document_title": self.document_title,
            "document_version": self.document_version,
            "domain": self.domain,
            "relative_path": self.relative_path,
            "organ": self.organ,
            "class_scope": self.class_scope,
            "sources": self.sources,
            "source_title": self.primary_source_title,
            "source_url": self.primary_source_url,
            "source_tier": self.primary_source_tier,
            "source_type": "guideline_policy" if self.is_safety_policy else "medical_literature",
            "citation": f"{self.primary_source_title} ({self.primary_source_url})" if self.primary_source_url else self.document_title,
            "last_reviewed": self.last_reviewed,
            "is_safety_policy": self.is_safety_policy,
            "claim_scope": self.claim_scope,
        }


class DocumentMetadataExtractor:
    """Extracts title, domain, class scope, and provenance sources from documents."""

    def __init__(self, registry: SourceRegistry | None = None) -> None:
        self.registry = registry or SourceRegistry()

    @staticmethod
    def derive_document_id(relative_path: str) -> str:
        """Derive a stable, deterministic document ID from relative path."""
        norm = relative_path.replace("\\", "/").strip("/").lower()
        # Remove common extension
        if norm.endswith(".md") or norm.endswith(".txt"):
            norm = norm.rsplit(".", 1)[0]
        # Replace non-alphanumeric characters with underscore
        clean_id = re.sub(r"[^a-z0-9_]+", "_", norm).strip("_")
        return f"doc_{clean_id}"

    def extract_sources(self, content: str) -> list[dict[str, Any]]:
        """Parse structured sources/references from document markdown."""
        sources: list[dict[str, Any]] = []
        pattern = r"##\s+(?:Sources|Source|References)\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if not match:
            return sources

        section_text = match.group(1)
        for line in section_text.splitlines():
            line = line.strip()
            if not line or not (line.startswith("-") or line.startswith("*")):
                continue
            item = line.lstrip("-* ").strip()
            url_match = re.search(r"https?://[^\s\)]+", item)
            if url_match:
                url = url_match.group(0).rstrip(".,;)")
                title_part = item[: url_match.start()].strip(" :-\t")
                resolved = self.registry.resolve(url, fallback_title=title_part or None)
                sources.append(
                    {
                        "title": resolved.title,
                        "url": resolved.url,
                        "tier": resolved.tier,
                    }
                )
        return sources

    def extract(
        self,
        file_path: Path,
        content: str,
        corpus_root: Path,
        version: str = "3.0.0",
    ) -> DocumentMetadata:
        """Extract complete DocumentMetadata from document content and path."""
        rel_path = str(file_path.relative_to(corpus_root)).replace("\\", "/")
        norm_path = rel_path.lower()

        # 1. Title extraction: first H1 or title-cased filename
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            doc_title = title_match.group(1).strip()
        else:
            doc_title = file_path.stem.replace("_", " ").title()

        # 2. Domain classification
        if "00_general" in norm_path:
            if any(kw in norm_path for kw in ["histopathology", "immunohistochemistry", "biopsy"]):
                domain = "histopathology"
            else:
                domain = "general_oncology"
        elif "01_colon" in norm_path or "colon_cancer" in norm_path:
            domain = "colon"
        elif "02_lung" in norm_path or "lung_cancer" in norm_path:
            domain = "lung"
        elif "03_classes" in norm_path:
            domain = "classifier_context"
        elif "04_comparisons" in norm_path:
            domain = "comparison"
        elif "05_question_answer" in norm_path:
            domain = "clinical_explanation"
        elif "06_safety" in norm_path:
            domain = "safety_policy"
        elif "developer_info" in norm_path:
            domain = "developer_info"
        elif "platform_info" in norm_path:
            domain = "platform_info"
        else:
            domain = "general_oncology"

        # 3. Class scope mapping
        class_scope: list[str] = []
        if "colon_adenocarcinoma" in norm_path:
            class_scope.append("colon_adenocarcinoma")
        if any(kw in norm_path for kw in ["benign_colonic", "benign_colon", "benign_lesions", "normal_colon"]):
            class_scope.append("benign_colonic_tissue")
        if "lung_adenocarcinoma" in norm_path:
            class_scope.append("lung_adenocarcinoma")
        if any(kw in norm_path for kw in ["benign_lung", "normal_lung"]):
            class_scope.append("benign_lung_tissue")
        if any(kw in norm_path for kw in ["lung_squamous", "squamous_cell"]):
            class_scope.append("lung_squamous_cell_carcinoma")

        if "all_five_classes" in norm_path:
            class_scope = sorted(list(SUPPORTED_CLASSIFIER_CLASSES))
        elif "colon_benign_vs_adenocarcinoma" in norm_path:
            class_scope = ["benign_colonic_tissue", "colon_adenocarcinoma"]
        elif "lung_adenocarcinoma_vs_squamous" in norm_path:
            class_scope = ["lung_adenocarcinoma", "lung_squamous_cell_carcinoma"]
        elif "lung_benign_vs_adenocarcinoma" in norm_path:
            class_scope = ["benign_lung_tissue", "lung_adenocarcinoma"]
        elif "lung_benign_vs_squamous" in norm_path:
            class_scope = ["benign_lung_tissue", "lung_squamous_cell_carcinoma"]

        # 4. Organ determination
        if "colon" in norm_path:
            organ = "colon"
        elif "lung" in norm_path:
            organ = "lung"
        else:
            organ = "general"

        # 5. Provenance extraction
        sources = self.extract_sources(content)
        primary_title = sources[0]["title"] if sources else None
        primary_url = sources[0]["url"] if sources else None
        primary_tier = sources[0]["tier"] if sources else None

        # Fallback for safety/comparison without inline sources
        is_safety = domain == "safety_policy"
        claim_scope = "policy" if is_safety else "educational"
        if not primary_url:
            if is_safety:
                primary_title = "OncoVision Clinical Safety & Scope Protocol"
                primary_url = "https://github.com/mahfujr403/OncoVision/tree/main/docs/safety"
                primary_tier = 1
            elif "all_five_classes" in norm_path:
                primary_title = "LC25000 Benchmark / CAP Protocols"
                primary_url = "https://arxiv.org/abs/1912.12142"
                primary_tier = 1

        resolved_class_scope: str | list[str] | None = None
        if len(class_scope) == 1:
            resolved_class_scope = class_scope[0]
        elif len(class_scope) > 1:
            resolved_class_scope = class_scope

        return DocumentMetadata(
            document_id=self.derive_document_id(rel_path),
            document_title=doc_title,
            document_version=version,
            domain=domain,
            relative_path=rel_path,
            organ=organ,
            class_scope=resolved_class_scope,
            sources=sources,
            primary_source_title=primary_title,
            primary_source_url=primary_url,
            primary_source_tier=primary_tier,
            last_reviewed="2026-10-06",
            is_safety_policy=is_safety,
            claim_scope=claim_scope,
        )
