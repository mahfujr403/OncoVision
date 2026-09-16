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
        
        # Apply any pending database migrations automatically on startup
        try:
            import os
            from alembic import command
            from alembic.config import Config
            import anyio

            ini_path = "alembic.ini" if os.path.exists("alembic.ini") else "backend/alembic.ini"
            if os.path.exists(ini_path):
                def _run_migrations():
                    cfg = Config(ini_path)
                    command.upgrade(cfg, "head")
                await anyio.to_thread.run_sync(_run_migrations)
                logger.info("Database migrations applied successfully on startup.")
        except Exception as mig_err:
            logger.warning("Auto-migration skipped or failed: %s", mig_err)

        # Ensure developer info and platform info are ingested in knowledge base
        try:
            from app.models.knowledge_embedding import KnowledgeEmbedding
            from app.database.session import AsyncSessionLocal
            from sqlalchemy import select
            async with AsyncSessionLocal() as db_session:
                has_dev_info = await db_session.scalar(
                    select(KnowledgeEmbedding.id).where(KnowledgeEmbedding.topic == 'developer_info').limit(1)
                )
                if not has_dev_info and settings.GOOGLE_API_KEY:
                    logger.info("Developer info missing from knowledge base, running auto-ingestion...")
                    from app.rag.embeddings import EmbeddingService
                    from app.rag.ingestion import DocumentIngestionPipeline
                    from app.llm.client import get_gemini_client
                    from pathlib import Path
                    
                    llm_client = get_gemini_client(settings.GOOGLE_API_KEY, settings.LLM_MODEL)
                    emb_svc = EmbeddingService(llm_client)
                    pipeline = DocumentIngestionPipeline(emb_svc)
                    
                    kb_dir = Path(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag", "knowledge_base"))
                    if kb_dir.exists():
                        await pipeline.ingest_directory(kb_dir, db_session)
                        logger.info("Knowledge base auto-sync completed successfully on startup.")
        except Exception as kb_err:
            logger.warning("Knowledge base auto-sync skipped: %s", kb_err)
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
