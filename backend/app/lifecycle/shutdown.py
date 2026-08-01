"""Application shutdown lifecycle logic."""

from app.core.logging import get_logger
from app.database.database import close_database_connection

logger = get_logger(__name__)


async def run_shutdown() -> None:
    """Execute all application shutdown tasks.

    Disposes of the database connection pool and logs a graceful shutdown
    message. No model unloading occurs in Phase 1.
    """
    await close_database_connection()
    logger.info("Application shutting down gracefully...")
