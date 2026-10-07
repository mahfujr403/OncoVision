"""Thread-safe, bounded, in-process query embedding cache (Phase 5.3).

Features:
- Normalized query keys (lowercased, whitespace-collapsed)
- One-way SHA-256 hash keys to guarantee zero raw-query or PHI persistence
- Bounded memory with LRU eviction (OrderedDict)
- Time-to-Live (TTL) expiration per entry
- Worker-local execution (no Redis or external dependencies required)
- Comprehensive observability stats (hits, misses, evictions, hit rate)
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from collections import OrderedDict
from typing import Any

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class QueryEmbeddingCache:
    """Thread-safe, bounded, worker-local LRU cache for query vector embeddings."""

    def __init__(
        self,
        max_size: int = 512,
        ttl_seconds: float = 3600.0,
        enabled: bool = True,
    ) -> None:
        self.max_size = max(1, max_size)
        self.ttl_seconds = max(0.001, float(ttl_seconds))
        self.enabled = enabled
        self._cache: OrderedDict[str, tuple[list[float], float]] = OrderedDict()
        self._lock = threading.Lock()

        # Telemetry metrics
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0

    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalize query text for deterministic cache key generation."""
        if not query:
            return ""
        # Lowercase, strip, and collapse multiple consecutive whitespaces into a single space
        return re.sub(r"\s+", " ", query.strip().lower())

    @classmethod
    def hash_key(cls, query: str) -> str:
        """Generate a one-way SHA-256 hash key from normalized query text.
        
        Guarantees that raw user text, patient references, or clinical terms
        are never retained in memory as cache keys.
        """
        normalized = cls.normalize_query(query)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, query: str) -> list[float] | None:
        """Retrieve a cached embedding if present and unexpired."""
        if not self.enabled or not query or not query.strip():
            return None

        key = self.hash_key(query)
        now = time.monotonic()

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            embedding, expire_at = self._cache[key]

            # Check TTL expiry
            if now > expire_at:
                del self._cache[key]
                self._misses += 1
                return None

            # Mark as most recently used
            self._cache.move_to_end(key)
            self._hits += 1
            return list(embedding)

    def set(self, query: str, embedding: list[float]) -> None:
        """Store an embedding in the cache with bounded capacity and TTL."""
        if not self.enabled or not query or not query.strip():
            return
        if not embedding or len(embedding) != 768:
            return

        key = self.hash_key(query)
        expire_at = time.monotonic() + self.ttl_seconds

        with self._lock:
            if key in self._cache:
                # Update existing and move to MRU
                self._cache[key] = (list(embedding), expire_at)
                self._cache.move_to_end(key)
                return

            # Check capacity before insertion
            if len(self._cache) >= self.max_size:
                # Pop least recently used (first item)
                self._cache.popitem(last=False)
                self._evictions += 1

            self._cache[key] = (list(embedding), expire_at)

    def invalidate(self, query: str) -> bool:
        """Remove a specific query from the cache if present."""
        key = self.hash_key(query)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from the cache and reset counters."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    def stats(self) -> dict[str, Any]:
        """Return cache health and telemetry statistics."""
        with self._lock:
            total_lookups = self._hits + self._misses
            hit_rate = round(self._hits / total_lookups, 4) if total_lookups > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": hit_rate,
                "enabled": self.enabled,
            }


# Worker-local singleton instance
_GLOBAL_EMBEDDING_CACHE: QueryEmbeddingCache | None = None
_CACHE_INIT_LOCK = threading.Lock()


def get_query_embedding_cache() -> QueryEmbeddingCache:
    """Retrieve the worker-local singleton query embedding cache."""
    global _GLOBAL_EMBEDDING_CACHE
    if _GLOBAL_EMBEDDING_CACHE is None:
        with _CACHE_INIT_LOCK:
            if _GLOBAL_EMBEDDING_CACHE is None:
                settings = get_settings()
                _GLOBAL_EMBEDDING_CACHE = QueryEmbeddingCache(
                    max_size=settings.RAG_EMBEDDING_CACHE_MAX_SIZE,
                    ttl_seconds=settings.RAG_EMBEDDING_CACHE_TTL_SECONDS,
                    enabled=settings.RAG_EMBEDDING_CACHE_ENABLED,
                )
    return _GLOBAL_EMBEDDING_CACHE
