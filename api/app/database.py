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
    # Note: pool_pre_ping is deliberately NOT enabled.
    # When Neon's free-tier auto-suspend was in play, pre-ping was
    # the defence against stale pooled connections surviving a
    # compute suspension. We upgraded to Neon's Launch plan + set
    # scale-to-zero to "off" on both branches (2026-10-27), so the
    # compute never suspends in normal operation. Keeping pre-ping
    # on would just add one ~160 ms Frankfurt-RTT round-trip per
    # request for no benefit. If we ever revert Neon to a tier that
    # auto-suspends, re-enable this.
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
