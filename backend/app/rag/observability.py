"""Production observability, telemetry, and structured logging for RAG (Phase 5.2).

Provides:
- Strongly typed error classifications (RAGErrorCategory).
- Privacy-safe structured logging emitting JSON-compatible events.
- Strict sanitization guaranteeing ZERO leakage of API keys, JWTs, database URLs,
  raw medical images, or raw user queries by default.
- High-resolution monotonic latency tracking across all major pipeline stages:
  classification_ms, safety_ms, retrieval_ms, grounding_ms, generation_ms,
  citation_validation_ms, total_latency_ms.
- Request correlation ID management and propagation.
- Lightweight in-process metrics collection without external SaaS dependencies.
- Strict prevention of false observability (events are only logged when executed).
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.core.settings import get_settings

logger = logging.getLogger("app.rag.observability")

# Standard event names mandated by Phase 5.2
EVENT_REQUEST_STARTED = "rag_request_started"
EVENT_REQUEST_COMPLETED = "rag_request_completed"
EVENT_SAFETY_REFUSAL = "rag_safety_refusal"
EVENT_RETRIEVAL_COMPLETED = "rag_retrieval_completed"
EVENT_RETRIEVAL_EMPTY = "rag_retrieval_empty"
EVENT_GROUNDING_REJECTED = "rag_grounding_rejected"
EVENT_GROUNDING_ACCEPTED = "rag_grounding_accepted"
EVENT_GENERATION_STARTED = "rag_generation_started"
EVENT_GENERATION_COMPLETED = "rag_generation_completed"
EVENT_GENERATION_FAILED = "rag_generation_failed"
EVENT_GENERATION_TIMEOUT = "rag_generation_timeout"
EVENT_CITATION_VALIDATION = "rag_citation_validation"


class RAGErrorCategory(str, Enum):
    """Categorized failure types for production debugging."""

    VALIDATION_ERROR = "validation_error"
    SAFETY_REFUSAL = "safety_refusal"
    RETRIEVAL_ERROR = "retrieval_error"
    EMBEDDING_ERROR = "embedding_error"
    GENERATION_TIMEOUT = "generation_timeout"
    GENERATION_API_ERROR = "generation_api_error"
    CITATION_VALIDATION_ERROR = "citation_validation_error"
    UNEXPECTED_ERROR = "unexpected_error"


_SECRET_KEY_PATTERNS = re.compile(
    r"(?:api[-_]?key|token|secret|password|bearer|authorization|database_url)",
    re.IGNORECASE,
)
_GOOGLE_API_KEY_REGEX = re.compile(r"AIza[0-9A-Za-z-_]{35}")
_JWT_REGEX = re.compile(r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*")
_DB_URL_CREDENTIAL_REGEX = re.compile(r"(?:postgresql|postgres|mysql|sqlite):\/\/[^\s@]+@")
_BASE64_IMAGE_REGEX = re.compile(r"data:image\/[a-zA-Z]+;base64,[A-Za-z0-9+/=]+")


def sanitize_request_id(candidate: str | None) -> str:
    """Validate and sanitize an incoming correlation ID or generate a new safe one."""
    if candidate and isinstance(candidate, str):
        candidate_clean = candidate.strip()
        # Accept safe alphanumeric characters, hyphens, and underscores up to 64 chars
        if 0 < len(candidate_clean) <= 64 and re.match(r"^[a-zA-Z0-9_\-]+$", candidate_clean):
            return candidate_clean
    return uuid.uuid4().hex[:12]


def sanitize_log_value(val: Any) -> Any:
    """Sanitize individual field values against secrets, credentials, and image blobs."""
    if isinstance(val, str):
        if _GOOGLE_API_KEY_REGEX.search(val):
            val = _GOOGLE_API_KEY_REGEX.sub("[REDACTED_API_KEY]", val)
        if _JWT_REGEX.search(val):
            val = _JWT_REGEX.sub("[REDACTED_JWT]", val)
        if _DB_URL_CREDENTIAL_REGEX.search(val):
            val = _DB_URL_CREDENTIAL_REGEX.sub("postgresql://[REDACTED_CREDENTIALS]@", val)
        if _BASE64_IMAGE_REGEX.search(val):
            val = _BASE64_IMAGE_REGEX.sub("[BASE64_IMAGE_REDACTED]", val)
        if len(val) > 200 and re.match(r"^[A-Za-z0-9+/=]{100,}$", val):
            val = "[BASE64_BLOB_REDACTED]"
        return val
    elif isinstance(val, dict):
        return sanitize_log_data(val)
    elif isinstance(val, (list, tuple, set)):
        return [sanitize_log_value(item) for item in val]
    return val


def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize entire payload dictionary according to HIPAA/PHI privacy rules."""
    sanitized: dict[str, Any] = {}
    settings = get_settings()

    for k, v in data.items():
        k_lower = k.lower()
        if _SECRET_KEY_PATTERNS.search(k_lower):
            sanitized[k] = "[REDACTED]"
            continue

        # Raw user query rule: default is no raw user query logging
        if k_lower in {"query", "user_message", "message", "prompt"}:
            if not getattr(settings, "RAG_LOG_QUERY_CONTENT", False):
                sanitized["query_length"] = len(str(v)) if v is not None else 0
                continue
            else:
                # Even if enabled, truncate and sanitize
                clean_q = sanitize_log_value(str(v))
                sanitized["query_truncated"] = clean_q[:64] + ("..." if len(clean_q) > 64 else "")
                continue

        # Prevent raw chunk body content or large medical text dumping into logs
        if k_lower in {"content", "raw_response", "formatted_context", "context_text"}:
            sanitized[f"{k}_length"] = len(str(v)) if v is not None else 0
            continue

        sanitized[k] = sanitize_log_value(v)

    return sanitized


@dataclass(frozen=True)
class RAGMetricsSnapshot:
    """Immutable point-in-time snapshot of RAG pipeline counters."""

    rag_requests_total: int
    rag_grounding_rejections_total: int
    rag_safety_refusals_total: int
    rag_retrieval_empty_total: int
    rag_generation_failures_total: int
    rag_generation_timeouts_total: int
    rag_requests_successful_total: int
    average_request_latency_ms: float
    average_retrieval_latency_ms: float
    average_generation_latency_ms: float


class RAGMetricsCollector:
    """Thread-safe, in-process metrics aggregator for the RAG subsystem."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rag_requests_total: int = 0
        self._rag_grounding_rejections_total: int = 0
        self._rag_safety_refusals_total: int = 0
        self._rag_retrieval_empty_total: int = 0
        self._rag_generation_failures_total: int = 0
        self._rag_generation_timeouts_total: int = 0
        self._rag_requests_successful_total: int = 0

        self._request_latency_sum_ms: float = 0.0
        self._request_latency_count: int = 0
        self._retrieval_latency_sum_ms: float = 0.0
        self._retrieval_latency_count: int = 0
        self._generation_latency_sum_ms: float = 0.0
        self._generation_latency_count: int = 0

    def record_event(self, event_name: str, payload: dict[str, Any]) -> None:
        """Update metrics counters based on recorded event."""
        with self._lock:
            if event_name == EVENT_REQUEST_STARTED:
                self._rag_requests_total += 1
            elif event_name == EVENT_SAFETY_REFUSAL:
                self._rag_safety_refusals_total += 1
            elif event_name == EVENT_RETRIEVAL_EMPTY:
                self._rag_retrieval_empty_total += 1
            elif event_name == EVENT_GROUNDING_REJECTED:
                self._rag_grounding_rejections_total += 1
            elif event_name == EVENT_GENERATION_TIMEOUT:
                self._rag_generation_timeouts_total += 1
                self._rag_generation_failures_total += 1
            elif event_name == EVENT_GENERATION_FAILED:
                self._rag_generation_failures_total += 1
            elif event_name == EVENT_REQUEST_COMPLETED:
                if payload.get("grounded", False):
                    self._rag_requests_successful_total += 1
                total_lat = payload.get("total_latency_ms")
                if total_lat is not None:
                    self._request_latency_sum_ms += float(total_lat)
                    self._request_latency_count += 1
            elif event_name == EVENT_RETRIEVAL_COMPLETED:
                ret_lat = payload.get("retrieval_ms")
                if ret_lat is not None:
                    self._retrieval_latency_sum_ms += float(ret_lat)
                    self._retrieval_latency_count += 1
            elif event_name == EVENT_GENERATION_COMPLETED:
                gen_lat = payload.get("generation_ms")
                if gen_lat is not None:
                    self._generation_latency_sum_ms += float(gen_lat)
                    self._generation_latency_count += 1

    def snapshot(self) -> RAGMetricsSnapshot:
        """Return an immutable snapshot of current counters."""
        with self._lock:
            avg_req = (
                self._request_latency_sum_ms / self._request_latency_count
                if self._request_latency_count > 0
                else 0.0
            )
            avg_ret = (
                self._retrieval_latency_sum_ms / self._retrieval_latency_count
                if self._retrieval_latency_count > 0
                else 0.0
            )
            avg_gen = (
                self._generation_latency_sum_ms / self._generation_latency_count
                if self._generation_latency_count > 0
                else 0.0
            )
            return RAGMetricsSnapshot(
                rag_requests_total=self._rag_requests_total,
                rag_grounding_rejections_total=self._rag_grounding_rejections_total,
                rag_safety_refusals_total=self._rag_safety_refusals_total,
                rag_retrieval_empty_total=self._rag_retrieval_empty_total,
                rag_generation_failures_total=self._rag_generation_failures_total,
                rag_generation_timeouts_total=self._rag_generation_timeouts_total,
                rag_requests_successful_total=self._rag_requests_successful_total,
                average_request_latency_ms=round(avg_req, 2),
                average_retrieval_latency_ms=round(avg_ret, 2),
                average_generation_latency_ms=round(avg_gen, 2),
            )

    def reset(self) -> None:
        """Reset counters for testing isolation."""
        with self._lock:
            self._rag_requests_total = 0
            self._rag_grounding_rejections_total = 0
            self._rag_safety_refusals_total = 0
            self._rag_retrieval_empty_total = 0
            self._rag_generation_failures_total = 0
            self._rag_generation_timeouts_total = 0
            self._rag_requests_successful_total = 0
            self._request_latency_sum_ms = 0.0
            self._request_latency_count = 0
            self._retrieval_latency_sum_ms = 0.0
            self._retrieval_latency_count = 0
            self._generation_latency_sum_ms = 0.0
            self._generation_latency_count = 0


default_rag_metrics_collector = RAGMetricsCollector()


def log_rag_event(event_name: str, payload: dict[str, Any], level: int = logging.INFO) -> dict[str, Any]:
    """Emit a structured, sanitized JSON log record and record in-process metrics."""
    data = dict(payload)
    data["event"] = event_name

    sanitized = sanitize_log_data(data)
    default_rag_metrics_collector.record_event(event_name, sanitized)

    settings = get_settings()
    if getattr(settings, "RAG_OBSERVABILITY_ENABLED", True):
        # Format as compact JSON message for structured log parsers
        try:
            json_msg = json.dumps(sanitized, default=str)
        except Exception:
            json_msg = str(sanitized)
        logger.log(level, "rag_event: %s", json_msg, extra={"rag_event": sanitized})

    return sanitized


class RAGTelemetryContext:
    """Manages the full lifecycle, latency breakdown, and event trace for a RAG request."""

    def __init__(
        self,
        request_id: str | None = None,
        chat_type: str = "knowledge",
        query: str = "",
        language: str = "en",
    ) -> None:
        self.request_id: str = sanitize_request_id(request_id)
        self.chat_type: str = chat_type
        self.query_length: int = len(query) if query else 0
        self.language: str = language
        self.start_time: float = time.perf_counter()

        # Monotonic latency breakdown (ms)
        self.classification_ms: float = 0.0
        self.safety_ms: float = 0.0
        self.retrieval_ms: float = 0.0
        self.grounding_ms: float = 0.0
        self.generation_ms: float = 0.0
        self.citation_validation_ms: float = 0.0
        self.total_latency_ms: float = 0.0

        # State tracking
        self.domain: str | None = None
        self.intent: str | None = None
        self.retrieved_chunks: int = 0
        self.top_similarity: float = 0.0
        self.mean_similarity: float = 0.0
        self.grounded: bool = False
        self.citations: int = 0
        self.safety_refused: bool = False
        self.refusal_reason: str | None = None
        self.error_category: str | None = None
        self.generation_model: str | None = None
        self.skipped_gemini: bool = True
        self._completed: bool = False

        # In-memory event audit log for testing and inspectability
        self.events: list[dict[str, Any]] = []

        # Record initial started event
        self.record_event(
            EVENT_REQUEST_STARTED,
            chat_type=self.chat_type,
            query_length=self.query_length,
            language=self.language,
        )

    def record_event(self, event_name: str, **kwargs: Any) -> dict[str, Any]:
        """Record an event with request_id and update context state."""
        payload = {"request_id": self.request_id, **kwargs}
        sanitized = log_rag_event(event_name, payload)
        self.events.append(sanitized)
        return sanitized

    def get_latency_breakdown(self) -> dict[str, float]:
        """Return the dictionary of captured pipeline latencies."""
        return {
            "classification_ms": round(self.classification_ms, 2),
            "safety_ms": round(self.safety_ms, 2),
            "retrieval_ms": round(self.retrieval_ms, 2),
            "grounding_ms": round(self.grounding_ms, 2),
            "generation_ms": round(self.generation_ms, 2),
            "citation_validation_ms": round(self.citation_validation_ms, 2),
            "total_latency_ms": round(self.total_latency_ms, 2),
        }

    def finish(
        self,
        grounded: bool = False,
        citations: int = 0,
        refusal_reason: str | None = None,
        error_category: str | None = None,
    ) -> dict[str, Any]:
        """Finalize request latency, update state, and emit rag_request_completed."""
        if self._completed:
            return self.events[-1] if self.events else {}

        self._completed = True
        self.total_latency_ms = round((time.perf_counter() - self.start_time) * 1000, 2)
        self.grounded = grounded
        self.citations = citations
        if refusal_reason:
            self.refusal_reason = refusal_reason
        if error_category:
            self.error_category = error_category

        return self.record_event(
            EVENT_REQUEST_COMPLETED,
            total_latency_ms=self.total_latency_ms,
            classification_ms=round(self.classification_ms, 2),
            safety_ms=round(self.safety_ms, 2),
            retrieval_ms=round(self.retrieval_ms, 2),
            grounding_ms=round(self.grounding_ms, 2),
            generation_ms=round(self.generation_ms, 2),
            citation_validation_ms=round(self.citation_validation_ms, 2),
            domain=self.domain,
            intent=self.intent,
            retrieved_chunks=self.retrieved_chunks,
            top_similarity=round(self.top_similarity, 4),
            grounded=self.grounded,
            citations=self.citations,
            safety_refused=self.safety_refused,
            refusal_reason=self.refusal_reason,
            error_category=self.error_category,
        )
