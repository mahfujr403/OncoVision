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
    ALLOWED_ORIGINS: str = "*"

    # Database configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/oncovision"

    # JWT / authentication configuration
    JWT_SECRET_KEY: str = _INSECURE_DEFAULT_JWT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12

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

    @property
    def allowed_origins_list(self) -> list[str]:
        """Return `ALLOWED_ORIGINS` as a parsed list of origin strings."""
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def is_production(self) -> bool:
        """Return True when running in a production environment."""
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Return True when running in a development environment."""
        return self.APP_ENV.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of `Settings`.

    Using `lru_cache` ensures environment variables are parsed once and the
    same settings instance is reused across the application lifetime.
    """
    return Settings()
