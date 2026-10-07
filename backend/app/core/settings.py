"""Centralized application settings.

All configuration is sourced from environment variables (optionally via a
`.env` file) using `pydantic-settings`. This is the single source of truth
for configuration values across the application. New configuration values
should be added here first.
"""

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Insecure default shipped only for local development convenience. Never
# valid in production -- see `Settings._validate_production_secrets`.
_INSECURE_DEFAULT_JWT_SECRET_KEY = "insecure-development-secret-key-change-me"


class Settings(BaseSettings):
    """Strongly typed application settings.

    Values are read from environment variables. See `.env.example` for the
    full list of supported variables and their defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application metadata
    APP_NAME: str = "OncoVision AI Backend"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # API configuration
    API_PREFIX: str = "/api/v1"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Upload / storage configuration
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    MODEL_STORAGE_PATH: str = "storage/models"
    UPLOAD_PATH: str = "storage/uploads"
    REPORT_PATH: str = "storage/reports"

    # Prediction image validation configuration
    # Bounds applied to every uploaded image before preprocessing, regardless
    # of which models are loaded. Per-model input size still comes only from
    # the Model Manifest.
    IMAGE_MIN_RESOLUTION: int = 32
    IMAGE_MAX_RESOLUTION: int = 4096

    # AI model registry configuration
    MODEL_MANIFEST_PATH: str = "app/ml/manifest/models.json"

    # Centralized Image Preprocessing configuration (ADR-018)
    # Fallback square input dimension used only when no `ModelRegistry` is
    # available or no model is currently enabled. Whenever the registry has
    # at least one enabled model, its manifest-defined `input_size` is used
    # instead -- this value never overrides the manifest.
    DEFAULT_PREPROCESSING_INPUT_SIZE: int = 224

    # AI runtime configuration
    # Number of enabled models, taken in ascending priority order, that the
    # AI Runtime Manager attempts to load eagerly at application startup.
    # Every other enabled model is registered and loaded lazily on first
    # request. This is priority-driven, never tied to a specific model ID,
    # so new manifest entries never require a code change.
    STARTUP_MODEL_LOAD_LIMIT: int = 3

    # Prediction History retrieval configuration (Phase 5.3, ADR-034)
    # Internal upper bound on the number of records returned by the
    # "list my prediction history" endpoint. Not exposed as a client-facing
    # pagination control -- that begins with Phase 5.4 (History Pagination
    # & Filtering) -- this value only keeps an unbounded query from being
    # issued against the database.
    PREDICTION_HISTORY_LIST_LIMIT: int = 200

    # Reporting export configuration (Phase 6.6, ADR-042)
    # Maximum number of Prediction History records a single Reporting
    # Foundation report, Prediction Analytics computation, CSV export, or
    # PDF export run may include. Enforced identically by
    # `ReportService`, `PredictionAnalyticsService`, `CSVExportService`,
    # and `PDFExportService` against `PredictionHistoryRepository.count_by_user()`
    # before any history rows are retrieved. Replaces the fixed,
    # non-configurable per-service bounds used through Phase 6.5 -- a
    # request whose matching history exceeds this bound is now rejected
    # with a `413` rather than silently truncated.
    REPORT_EXPORT_MAX_ROWS: int = 1000

    # Hard safety cap, in bytes, on the size of a single generated CSV or
    # PDF export document (Phase 6.6, ADR-042). Guards against an
    # unexpectedly large in-memory/response document even when
    # `REPORT_EXPORT_MAX_ROWS` is respected -- for example, an unusually
    # large number of individual model predictions per record. Checked by
    # `CSVExportService`/`PDFExportService` only after generation, as a
    # last line of defense; not expected to be reached under normal
    # operation at the default `REPORT_EXPORT_MAX_ROWS`.
    REPORT_EXPORT_MAX_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB

    # CORS
    ALLOWED_ORIGINS: str = "https://oncovision-live.netlify.app"

    # Database configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/oncovision"

    # JWT / authentication configuration
    JWT_SECRET_KEY: str = _INSECURE_DEFAULT_JWT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12

    # LLM / Gemini API configuration (Phase 11 — LLM + RAG Integration)
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    LLM_EMBEDDING_MODEL: str = "gemini-embedding-2"
    LLM_MAX_TOKENS: int = 512
    LLM_TEMPERATURE: float = 0.2

    # RAG configuration (Phase 11 & Phase 3)
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 4
    RAG_SIMILARITY_THRESHOLD: float = 0.55
    RAG_MAX_CONTEXT_CHUNKS: int = 5
    RAG_CANDIDATE_POOL_SIZE: int = 15

    # Chat rate limiting (Phase 11)
    CHAT_RATE_LIMIT_MAX_REQUESTS: int = 20
    CHAT_RATE_LIMIT_WINDOW_SECONDS: int = 3600

    # Chat input boundary hardening (Phase 6.2-B, FINDING-06)
    CHAT_MAX_MESSAGE_LENGTH: int = 2000

    # System diagnostic LLM rate limiting (Phase 6.1-A)
    SYSTEM_TEST_LLM_RATE_LIMIT_MAX_REQUESTS: int = 5
    SYSTEM_TEST_LLM_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Authentication rate limiting configuration (Phase 6.1-D, FINDING-05)
    AUTH_LOGIN_RATE_LIMIT_MAX_REQUESTS: int = 5
    AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60
    AUTH_REGISTER_RATE_LIMIT_MAX_REQUESTS: int = 3
    AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS: int = 3600

    # Security headers / HSTS configuration (Phase 6.1-C, ADR-043)
    HSTS_ENABLED: bool = True
    HSTS_MAX_AGE_SECONDS: int = 31536000  # 1 year
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    HSTS_PRELOAD: bool = False

    # Knowledge Base & Ingestion configuration (Phase 2)
    KNOWLEDGE_BASE_PATH: str = "knowledge_base/oncovision_medical_knowledgebase_v3"
    AUTO_INGEST_ON_STARTUP: bool = False

    # Grounded RAG Generation configuration (Phase 4)
    RAG_GENERATION_MODEL: str = "gemini-3.5-flash-lite"
    RAG_GENERATION_TEMPERATURE: float = 0.2
    RAG_GENERATION_MAX_OUTPUT_TOKENS: int = 768
    RAG_GENERATION_TIMEOUT: float = 30.0
    RAG_GENERATION_MAX_RETRIES: int = 2

    # RAG Grounding & Relevance Evaluation configuration (Phase 5.1)
    RAG_MIN_GROUNDING_SIMILARITY: float = 0.75
    RAG_STRONG_GROUNDING_SIMILARITY: float = 0.82

    # RAG Observability & Reliability configuration (Phase 5.2)
    RAG_OBSERVABILITY_ENABLED: bool = True
    RAG_LOG_QUERY_CONTENT: bool = False

    # RAG Production Performance & Optimization configuration (Phase 5.3)
    RAG_EMBEDDING_CACHE_ENABLED: bool = True
    RAG_EMBEDDING_CACHE_MAX_SIZE: int = 512
    RAG_EMBEDDING_CACHE_TTL_SECONDS: float = 3600.0

    @field_validator("RAG_GENERATION_MODEL")
    @classmethod
    def validate_rag_generation_model(cls, value: str) -> str:
        """Upgrade deprecated models to currently supported Google models."""
        if value in {"gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"}:
            return "gemini-3.5-flash-lite"
        return value

    @field_validator("LLM_MODEL")
    @classmethod
    def validate_llm_model(cls, value: str) -> str:
        """Upgrade deprecated models to currently supported Google models."""
        if value in {"gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite"}:
            return "gemini-3.5-flash-lite"
        return value

    @field_validator("LLM_EMBEDDING_MODEL")
    @classmethod
    def validate_llm_embedding_model(cls, value: str) -> str:
        """Upgrade deprecated embedding models."""
        if value in {"text-embedding-004"}:
            return "gemini-embedding-2"
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Ensure the configured log level is a valid logging level name."""
        normalized = value.upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got '{value}'"
            )
        return normalized

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Refuse to start with an insecure secret when `APP_ENV=production`.

        The insecure default is intentionally kept as the out-of-the-box
        development value (`.env.example` ships without one, so an
        unconfigured dev environment still boots). It must never reach a
        production deployment, so this only takes effect when `APP_ENV` is
        explicitly `production` -- development and test environments are
        unaffected.
        """
        if self.is_production and self.JWT_SECRET_KEY == _INSECURE_DEFAULT_JWT_SECRET_KEY:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a strong, unique value via the "
                "environment when APP_ENV=production. Refusing to start with "
                "the insecure development default."
            )
        return self

    @model_validator(mode="after")
    def _validate_production_cors(self) -> "Settings":
        """Refuse insecure CORS configurations when `APP_ENV=production`.

        Production must never allow wildcard origins (`*`) while credentials are enabled.
        """
        if self.is_production:
            raw_origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
            if self.ALLOWED_ORIGINS.strip() == "*" or "*" in raw_origins:
                raise ValueError(
                    "ALLOWED_ORIGINS cannot contain '*' in production when credentials are "
                    "enabled. Specify explicit trusted origin(s), e.g. 'https://oncovision-live.netlify.app'."
                )
            if not raw_origins:
                raise ValueError(
                    "ALLOWED_ORIGINS must contain at least one trusted origin in production."
                )
        return self

    @property
    def allowed_origins_list(self) -> list[str]:
        """Return `ALLOWED_ORIGINS` as a parsed list of explicitly trusted origin strings."""
        if self.is_production:
            origins = [
                origin.strip()
                for origin in self.ALLOWED_ORIGINS.split(",")
                if origin.strip() and origin.strip() != "*"
            ]
            canonical_origin = "https://oncovision-live.netlify.app"
            if canonical_origin not in origins:
                origins.append(canonical_origin)
            return origins

        # In development: if configured with '*', resolve to canonical production + local dev origins
        # rather than literal ['*'], preventing insecure wildcard origin reflection with credentials.
        if self.ALLOWED_ORIGINS.strip() == "*":
            return [
                "https://oncovision-live.netlify.app",
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
            ]

        origins = [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip() and origin.strip() != "*"
        ]
        canonical_origin = "https://oncovision-live.netlify.app"
        if canonical_origin not in origins:
            origins.append(canonical_origin)

        for dev_origin in ("http://localhost:5173", "http://localhost:3000"):
            if dev_origin not in origins:
                origins.append(dev_origin)

        return origins

    @property
    def cors_origin_regex(self) -> str | None:
        """Return regex for matching local development origins, or None in production.

        In production, arbitrary subdomain regex matching is strictly disabled.
        Only explicit origins in `allowed_origins_list` are accepted.
        """
        if self.is_production:
            return None
        return r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    @property
    def is_production(self) -> bool:
        """Return True when running in a production environment."""
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Return True when running in a development environment."""
        return self.APP_ENV.lower() == "development"

    @property
    def hsts_header_value(self) -> str:
        """Construct Strict-Transport-Security header value (Phase 6.1-C, FINDING-08)."""
        parts = [f"max-age={self.HSTS_MAX_AGE_SECONDS}"]
        if self.HSTS_INCLUDE_SUBDOMAINS:
            parts.append("includeSubDomains")
        if self.HSTS_PRELOAD:
            parts.append("preload")
        return "; ".join(parts)


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of `Settings`.

    Using `lru_cache` ensures environment variables are parsed once and the
    same settings instance is reused across the application lifetime.
    """
    return Settings()
