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
    "HTTPError",
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
async def test_public_openapi_advertises_webhooks_tag(async_client):
    """The Webhooks tag is description-only — no operations reference it —
    but the public Swagger UI needs it so lenders see signature
    verification + retry guidance."""
    r = await async_client.get("/openapi.json")
    tag_names = {t["name"] for t in r.json().get("tags", [])}
    assert "Webhooks" in tag_names
    webhooks_tag = next(t for t in r.json()["tags"] if t["name"] == "Webhooks")
    desc = webhooks_tag.get("description", "")
    assert "X-PayPredict-Signature" in desc
    assert "hmac" in desc.lower()


@pytest.mark.asyncio
async def test_lender_routes_document_401_and_429(async_client):
    """Every lender-facing operation must surface both 401 and 429 in its
    responses so SDK code-generators emit retry / backoff logic."""
    r = await async_client.get("/openapi.json")
    paths = r.json()["paths"]
    # Lender-facing ops (everything that isn't /v1/health*)
    lender_ops = [
        (path, method)
        for path, methods in paths.items()
        for method in methods
        if not path.startswith("/v1/health")
    ]
    assert lender_ops, "Sanity: there should be lender-facing operations"
    for path, method in lender_ops:
        codes = set(paths[path][method].get("responses", {}).keys())
        assert "401" in codes, f"{method.upper()} {path} missing 401 response"
        assert "429" in codes, f"{method.upper()} {path} missing 429 response"


@pytest.mark.asyncio
async def test_429_response_documents_rate_limit_headers(async_client):
    """The 429 response must surface Retry-After + X-RateLimit-* headers so
    lender retry logic can read them without guessing."""
    r = await async_client.get("/openapi.json")
    score_op = r.json()["paths"]["/v1/score"]["post"]
    headers = score_op["responses"]["429"].get("headers", {})
    for required in ("Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
        assert required in headers, f"429 missing {required} header doc"


@pytest.mark.asyncio
async def test_openapi_version_matches_pyproject(async_client):
    """OpenAPI version is read from pyproject.toml at startup, not hardcoded."""
    from app.config import APP_VERSION

    r = await async_client.get("/openapi.json")
    assert r.json()["info"]["version"] == APP_VERSION
    # Sanity: APP_VERSION should not be the fallback string returned when
    # pyproject.toml can't be read.
    assert APP_VERSION != "0.0.0", (
        "pyproject.toml fallback hit — version did not load from disk"
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
