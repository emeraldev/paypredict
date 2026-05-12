"""FastAPI entry point.

All endpoints stay at their original `/v1/...` paths. The OpenAPI
surface is split in two by tag — every operation tagged with a value in
`docs_config.PUBLIC_TAGS` appears in the public Swagger UI at `/docs`;
the full schema (everything, including dashboard-internal endpoints) is
served at `/docs/internal`, which is disabled in production.
"""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse

from app.api.docs import get_internal_openapi_schema, get_public_openapi_schema
from app.api.v1 import (
    alerts,
    alerts_config,
    analytics,
    api_keys,
    auth,
    backtest,
    bulk_score,
    health,
    notifications,
    outcomes,
    outcomes_list,
    scores,
    scores_list,
    team,
    weights,
)
from app.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    yield
    from app.database import engine

    await engine.dispose()


# Disable the default docs endpoints — we serve custom filtered versions
# below. Disabling `openapi_url` also stops FastAPI from auto-routing
# /openapi.json, so we own that path explicitly.
app = FastAPI(
    title="PayPredict API",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All routes live under /v1 — paths do not change with the docs split.
app.include_router(health.router, prefix="/v1")
app.include_router(scores.router, prefix="/v1")
app.include_router(bulk_score.router, prefix="/v1")
app.include_router(outcomes.router, prefix="/v1")
app.include_router(analytics.router, prefix="/v1")
app.include_router(weights.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")
app.include_router(scores_list.router, prefix="/v1")
app.include_router(outcomes_list.router, prefix="/v1")
app.include_router(notifications.router, prefix="/v1")
app.include_router(backtest.router, prefix="/v1")
app.include_router(alerts.router, prefix="/v1")
app.include_router(api_keys.router, prefix="/v1")
app.include_router(team.router, prefix="/v1")
app.include_router(alerts_config.router, prefix="/v1")


# ---- Public docs (lenders) ----


@app.get("/openapi.json", include_in_schema=False)
async def public_openapi() -> JSONResponse:
    return JSONResponse(get_public_openapi_schema(app))


@app.get("/docs", include_in_schema=False)
async def public_docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="PayPredict API",
    )


@app.get("/redoc", include_in_schema=False)
async def public_redoc():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="PayPredict API",
    )


# ---- Internal docs (dev + dashboard) ----

if settings.environment != "production":

    @app.get("/openapi-internal.json", include_in_schema=False)
    async def internal_openapi() -> JSONResponse:
        return JSONResponse(get_internal_openapi_schema(app))

    @app.get("/docs/internal", include_in_schema=False)
    async def internal_docs():
        return get_swagger_ui_html(
            openapi_url="/openapi-internal.json",
            title="PayPredict Internal API",
        )
