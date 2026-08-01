"""Database configuration entry point.

Exposes the resolved `Base`, `get_db` dependency, and connection lifecycle
helpers used during application startup and shutdown. Business logic and
repositories should import from this module rather than reaching into
`session.py` or `base.py` directly.
"""

from sqlalchemy import text

from app.database.base import Base
from app.database.session import AsyncSessionLocal, engine, get_db

__all__ = [
    "Base",
    "AsyncSessionLocal",
    "engine",
    "get_db",
    "check_database_connection",
    "close_database_connection",
]


async def check_database_connection() -> None:
    """Verify database connectivity by executing a lightweight query.

    Raises:
        Exception: Propagated if the database cannot be reached, so the
            caller can decide how to handle a failed startup check.
    """
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def close_database_connection() -> None:
    """Dispose of the async engine's connection pool on application shutdown."""
    await engine.dispose()
