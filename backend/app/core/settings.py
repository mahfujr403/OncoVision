"""Centralized application settings.

All configuration is sourced from environment variables (optionally via a
`.env` file) using `pydantic-settings`. This is the single source of truth
for configuration values across the application. New configuration values
should be added here first.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    STARTUP_MODEL_LOAD_LIMIT: int = 2

    # Prediction History retrieval configuration (Phase 5.3, ADR-034)
    # Internal upper bound on the number of records returned by the
    # "list my prediction history" endpoint. Not exposed as a client-facing
    # pagination control -- that begins with Phase 5.4 (History Pagination
    # & Filtering) -- this value only keeps an unbounded query from being
    # issued against the database.
    PREDICTION_HISTORY_LIST_LIMIT: int = 200

    # CORS
    ALLOWED_ORIGINS: str = "*"

    # Database configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/oncovision"

    # JWT / authentication configuration
    JWT_SECRET_KEY: str = "insecure-development-secret-key-change-me"
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
