"""Tests for the startup schema-version check.

Happy-path uses the real test engine (which conftest keeps at head).
Sad-paths mock `current_db_version` — the query itself is a single
`SELECT version_num FROM alembic_version`, not the interesting part.
The interesting part is: does the check produce a clear, refuse-loudly
message for each shape of drift?
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.startup_checks import (
    SchemaVersionMismatch,
    assert_db_at_head,
    expected_head,
)


def test_expected_head_is_a_12_char_revision():
    """Sanity: expected_head reads the versions/ directory and returns
    the current Alembic head as a 12-char hex string."""
    head = expected_head()
    assert isinstance(head, str)
    assert len(head) == 12
    assert all(c in "0123456789abcdef" for c in head)


@pytest.mark.asyncio
async def test_happy_path_returns_when_db_at_head(db_session):
    """conftest migrates the test DB to head. `assert_db_at_head`
    should return without raising."""
    await assert_db_at_head(db_session.bind)


@pytest.mark.asyncio
async def test_raises_when_db_is_behind(db_session):
    """A DB stuck at an older revision blocks startup with a message
    naming both the actual and expected revisions."""
    with patch(
        "app.startup_checks.current_db_version",
        AsyncMock(return_value="5b17a75fd7b3"),  # a real prior revision
    ):
        with pytest.raises(SchemaVersionMismatch, match="5b17a75fd7b3"):
            await assert_db_at_head(db_session.bind)


@pytest.mark.asyncio
async def test_raises_when_db_is_ahead(db_session):
    """A DB at a revision this code doesn't know about is also refused.
    Common trigger: rolled back the code but not the schema."""
    with patch(
        "app.startup_checks.current_db_version",
        AsyncMock(return_value="ffffffffffff"),
    ):
        with pytest.raises(SchemaVersionMismatch, match="ffffffffffff"):
            await assert_db_at_head(db_session.bind)


@pytest.mark.asyncio
async def test_raises_when_alembic_version_table_missing(db_session):
    """No alembic_version table means the DB was never migrated.
    Message tells the operator exactly how to fix it."""
    with patch(
        "app.startup_checks.current_db_version",
        AsyncMock(return_value=None),
    ):
        with pytest.raises(SchemaVersionMismatch, match="alembic upgrade head"):
            await assert_db_at_head(db_session.bind)


@pytest.mark.asyncio
async def test_health_detailed_reports_schema_ok_at_head(async_client):
    """The /health/detailed endpoint exposes the schema check so
    external monitors can alert on drift even after startup succeeded
    (e.g. someone runs `alembic downgrade -1` on a live DB)."""
    r = await async_client.get("/v1/health/detailed")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["schema"] == "ok"
    assert body["schema_version"] == body["schema_expected"]
    assert len(body["schema_version"]) == 12


@pytest.mark.asyncio
async def test_health_detailed_reports_mismatch_when_versions_diverge(async_client):
    """Force a mismatch via monkeypatch and verify the endpoint
    correctly reports it as degraded."""
    with patch(
        "app.startup_checks.current_db_version",
        AsyncMock(return_value="deadbeefdead"),
    ):
        r = await async_client.get("/v1/health/detailed")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["schema"] == "mismatch"
    assert body["schema_version"] == "deadbeefdead"
    assert body["schema_expected"] != "deadbeefdead"
