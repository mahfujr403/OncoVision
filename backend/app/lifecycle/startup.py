"""Application startup lifecycle logic."""

from app.core.config import ensure_storage_directories, settings
from app.core.logging import configure_logging, get_logger
from app.database.database import check_database_connection
from app.dependencies.services import get_ai_runtime_manager, get_model_registry

logger = get_logger(__name__)

_STARTUP_BANNER = """
==================================================
  {app_name}
  Version: {app_version}
  Environment: {app_env}
  Host: {host}:{port}
  Docs: /docs
==================================================
"""


async def run_startup() -> None:
    """Execute all application startup tasks.

    Initializes logging, validates and creates required storage
    directories, validates the AI model manifest, and prints a startup
    banner. No TensorFlow model loading occurs in this phase.
    """
    configure_logging()
    logger.info("Starting application startup sequence...")

    ensure_storage_directories()
    logger.info("Storage directories validated and ready.")

    try:
        model_registry = get_model_registry()
        logger.info(
            "Model manifest validated successfully (%d models registered).",
            len(model_registry.get_all_models()),
        )
    except Exception:
        logger.error(
            "Model manifest validation failed. AI model infrastructure "
            "endpoints will be unavailable until this is resolved.",
            exc_info=True,
        )

    try:
        await check_database_connection()
        logger.info("Database connection verified successfully.")
    except Exception:
        logger.error(
            "Database connection check failed. Authentication and other "
            "database-backed endpoints will be unavailable until this is "
            "resolved.",
            exc_info=True,
        )

    try:
        runtime_manager = get_ai_runtime_manager()
        await runtime_manager.initialize()
        loaded_models = await runtime_manager.health_service.loaded_models()
        logger.info(
            "AI Runtime Manager initialized (%d model(s) loaded and ready).",
            len(loaded_models),
        )
    except Exception:
        logger.error(
            "AI Runtime Manager initialization failed. Prediction-dependent "
            "endpoints will be unavailable until this is resolved.",
            exc_info=True,
        )

    banner = _STARTUP_BANNER.format(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        app_env=settings.APP_ENV,
        host=settings.HOST,
        port=settings.PORT,
    )
    print(banner)
    logger.info("Application startup completed successfully.")
