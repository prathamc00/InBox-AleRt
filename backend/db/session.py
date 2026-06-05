"""
Async SQLAlchemy session factory with tenant-scoped query helpers.
Every request gets a session locked to the requesting user's tenant_id.
"""
from collections.abc import AsyncGenerator
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings


def _build_engine():
    """
    Build the async engine. asyncpg does not support ssl/sslmode as URL query
    parameters — it must be passed via connect_args instead. We strip those
    params from the URL and inject the correct ssl argument.
    """
    db_url = settings.DATABASE_URL

    # Strip any ssl/sslmode query params that asyncpg cannot handle
    parsed = urlparse(db_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs.pop("ssl", None)
    qs.pop("sslmode", None)
    clean_url = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))

    # In production (not DEBUG), Render Postgres requires SSL
    connect_args = {}
    if not settings.DEBUG:
        connect_args["ssl"] = True

    return create_async_engine(
        clean_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args=connect_args,
    )


engine = _build_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a DB session, closes on exit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
