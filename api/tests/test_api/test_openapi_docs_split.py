"""Regression tests for the public / internal OpenAPI docs split.

These tests pin the public surface — every endpoint and every Pydantic
schema that appears on `/openapi.json`. They exist because the split is
tag-driven and a typo (or a forgotten tag) on a new endpoint would
silently leak it into the lender-facing Swagger UI.

When you add a new endpoint:

  - If it is lender-facing, add its path to `EXPECTED_PUBLIC_PATHS` and
    any new request/response schemas it introduces to
    `EXPECTED_PUBLIC_SCHEMAS`.

  - If it is dashboard-only, do nothing here. The test enforces that
    nothing dashboard-shaped (Auth / Backtest / Team / etc.) leaks.
"""
import pytest


EXPECTED_PUBLIC_PATHS = {
    "/v1/analytics/accuracy",
    "/v1/analytics/collection-rate",
    "/v1/analytics/factors",
    "/v1/analytics/summary",
    "/v1/config/weights",
    "/v1/health",
    "/v1/health/detailed",
    "/v1/outcomes",
    "/v1/score",
    "/v1/score/bulk",
    "/v1/score/bulk/{job_id}",
}

EXPECTED_PUBLIC_SCHEMAS = {
    "AccuracyResponse",
    "AnalyticsSummaryResponse",
    "BulkScoreItem",
    "BulkScoreRequest",
    "CollectionRatePoint",
    "CollectionRateResponse",
    "ConfusionMatrix",
    "CustomerData",
    "FactorBreakdown",
    "FactorContributionItem",
    "FactorsResponse",
    "HTTPValidationError",
    "OutcomeRequest",
    "OutcomeResponse",
    "PredictionAccuracy",
    "RiskDistribution",
    "ScoreRequest",
    "ScoreResponse",
    "ValidationError",
}

# Substrings that should never appear in the public schema name set.
# Catches the failure mode where a new internal-only Pydantic model gets
# accidentally pulled in via a reference from a public schema.
INTERNAL_NAME_SUBSTRINGS = (
    "Auth",
    "Login",
    "Logout",
    "Token",
    "Notification",
    "Backtest",
    "Team",
    "ApiKey",
    "AlertsConfig",
    "UserResponse",
    "UserRole",
)


@pytest.mark.asyncio
async def test_public_openapi_paths_match_expected(async_client):
    r = await async_client.get("/openapi.json")
    assert r.status_code == 200
    paths = set(r.json()["paths"].keys())
    extra = paths - EXPECTED_PUBLIC_PATHS
    missing = EXPECTED_PUBLIC_PATHS - paths
    assert not extra, (
        f"Unexpected paths leaked into the public docs: {sorted(extra)}. "
        "If these are meant to be public, add them to EXPECTED_PUBLIC_PATHS. "
        "If not, retag the route with an internal tag."
    )
    assert not missing, (
        f"Expected public paths are missing: {sorted(missing)}. "
        "Did a route get removed or untagged?"
    )


@pytest.mark.asyncio
async def test_public_openapi_schemas_match_expected(async_client):
    r = await async_client.get("/openapi.json")
    assert r.status_code == 200
    schemas = set(r.json().get("components", {}).get("schemas", {}).keys())
    extra = schemas - EXPECTED_PUBLIC_SCHEMAS
    missing = EXPECTED_PUBLIC_SCHEMAS - schemas
    assert not extra, (
        f"Unexpected schemas leaked into the public docs: {sorted(extra)}. "
        "If these are meant to be public, add them to EXPECTED_PUBLIC_SCHEMAS."
    )
    assert not missing, f"Expected public schemas are missing: {sorted(missing)}."


@pytest.mark.asyncio
async def test_public_openapi_has_no_internal_typed_names(async_client):
    r = await async_client.get("/openapi.json")
    schemas = set(r.json().get("components", {}).get("schemas", {}).keys())
    offending = [
        s for s in schemas
        if any(needle in s for needle in INTERNAL_NAME_SUBSTRINGS)
    ]
    assert not offending, (
        f"Internal-looking schemas in public docs: {offending}. "
        "Either retag the consuming endpoint as internal or rename the schema."
    )


@pytest.mark.asyncio
async def test_internal_openapi_includes_public_and_dashboard(async_client):
    r = await async_client.get("/openapi-internal.json")
    assert r.status_code == 200
    paths = set(r.json()["paths"].keys())
    assert EXPECTED_PUBLIC_PATHS.issubset(paths), (
        "Internal docs should include every public path too."
    )
    # Spot-check a few dashboard-only paths.
    for dashboard_path in ("/v1/auth/login", "/v1/notifications", "/v1/backtest"):
        assert dashboard_path in paths, (
            f"Dashboard path {dashboard_path} missing from internal docs"
        )


@pytest.mark.asyncio
async def test_internal_openapi_disabled_in_production(monkeypatch, async_client):
    """When both gates flip (env=production AND/OR internal_docs_enabled=False),
    the internal endpoints stop responding. We toggle the flag at the
    settings layer; the route is registered at import time so this test
    asserts the settings property, not a live 404 (would require app
    rebuild)."""
    from app.config import Settings

    prod = Settings(environment="production", internal_docs_enabled=True)
    assert prod.internal_docs_visible is False, "production must hide internal docs"

    disabled = Settings(environment="development", internal_docs_enabled=False)
    assert disabled.internal_docs_visible is False, (
        "internal_docs_enabled=False must hide internal docs even in dev"
    )

    dev = Settings(environment="development", internal_docs_enabled=True)
    assert dev.internal_docs_visible is True, "dev default should show internal docs"
