from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=10,
    max_overflow=20,
    # Disable asyncpg's named prepared-statement cache. Required when
    # the DATABASE_URL points at a PgBouncer transaction-pooling
    # endpoint (Neon's `-pooler` hostname, the default we use in Fly).
    # Transaction-mode pooling reuses backend connections across
    # clients, so cached statement names collide across requests and
    # asyncpg raises DuplicatePreparedStatementError on the second
    # call. Setting the cache size to zero makes asyncpg re-parse
    # each statement — ~sub-ms overhead and the only safe mode under
    # a transaction pooler. Non-pooled Postgres (local Docker, direct
    # Neon endpoint) is unaffected because the cache was per-session.
    connect_args={"statement_cache_size": 0},
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
