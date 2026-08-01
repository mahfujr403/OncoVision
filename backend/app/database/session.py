"""Async database engine and session management.

Provides the shared async engine, session factory, and `get_db` FastAPI
dependency. All repositories obtain their `AsyncSession` through `get_db`,
ensuring consistent transaction and connection handling across the
application.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped `AsyncSession`, rolling back on error.

    Services are responsible for committing their own unit of work;
    this dependency guarantees the session is rolled back and closed
    if a service or repository raises.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
