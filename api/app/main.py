from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1 import (
    alerts_config,
    analytics,
    api_keys,
    auth,
    health,
    outcomes,
    outcomes_list,
    scores,
    scores_list,
    team,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    yield
    # Shutdown
    from app.database import engine

    await engine.dispose()


app = FastAPI(
    title="PayPredict",
    description="Pre-collection risk scoring API for instalment lenders in Africa",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/v1")

# Lender-facing API-key endpoints (Phase 1)
app.include_router(scores.router, prefix="/v1")
app.include_router(outcomes.router, prefix="/v1")

# Dashboard session-auth endpoints (Phase 2.5 — stubs return 501 until each
# step lands)
app.include_router(auth.router, prefix="/v1")
app.include_router(scores_list.router, prefix="/v1")
app.include_router(outcomes_list.router, prefix="/v1")
app.include_router(analytics.router, prefix="/v1")
app.include_router(api_keys.router, prefix="/v1")
app.include_router(team.router, prefix="/v1")
app.include_router(alerts_config.router, prefix="/v1")
