from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=10,
    max_overflow=20,
    # - statement_cache_size=0: required when the DATABASE_URL points
    #   at a PgBouncer transaction-pooling endpoint (Neon's `-pooler`
    #   hostname, the default we use in Fly). Transaction-mode pooling
    #   reuses backend connections across clients, so cached statement
    #   names collide across requests and asyncpg raises
    #   DuplicatePreparedStatementError on the second call. Zero cache
    #   = asyncpg re-parses each statement (~sub-ms). Non-pooled
    #   Postgres (local Docker, direct Neon endpoint) is unaffected.
    # - timeout=90: Neon's free tier suspends computes after 5 min
    #   idle; the first reconnect triggers a cold-start of ~10-30 s
    #   (occasionally longer). asyncpg's default connect timeout is
    #   60s which can trip on a slow cold-start. 90s rides those out.
    #   Covers production too — a lender's first API call after a
    #   quiet period shouldn't 500.
    connect_args={"statement_cache_size": 0, "timeout": 90},
    # Pessimistic connection check — hands SQLAlchemy's pool a quick
    # SELECT 1 before yielding a stale connection. Catches the case
    # where Neon suspended the compute AFTER a connection was pooled
    # here; without this, the first query after suspension would
    # raise ConnectionDoesNotExistError instead of silently
    # reconnecting. Costs one round-trip per checkout (~ms); cheap
    # vs the 500 to the lender.
    pool_pre_ping=True,
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
