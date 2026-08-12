"""Prove every migration guard fires end-to-end.

Without this, guards are keyed on "does customer data exist", and PR A's
round-trip CI runs against an empty DB — so all guards find zero rows,
take the proceed branch, and the refuse branch (the entire point of the
guard) is never exercised. Dead code that passes green.

Each parametrized case:
  1. Fresh isolated DB.
  2. Upgrade to the target revision (using `FORCE_DESTRUCTIVE_UPGRADE=all`
     for anything gated on upgrade).
  3. Seed the smallest row that triggers the specific guard.
  4. Run the downgrade WITHOUT the ack env var.
  5. Assert `RuntimeError` with the guard's signature phrase.
  6. Assert the ack path (revision-specific env var) proceeds.
"""
from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine


_API_DIR = Path(__file__).resolve().parent.parent


def _dsn(dbname: str, *, sync: bool = False) -> str:
    scheme = "postgresql+psycopg2" if sync else "postgresql+asyncpg"
    return f"{scheme}://paypredict:localdev@localhost:5434/{dbname}"


def _admin_dsn() -> str:
    return _dsn("paypredict_dev", sync=True)


def _create_fresh_db(dbname: str) -> None:
    admin = create_engine(_admin_dsn(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(sa.text(f"DROP DATABASE IF EXISTS {dbname}"))
        conn.execute(sa.text(f"CREATE DATABASE {dbname} OWNER paypredict"))
    admin.dispose()


def _drop_db(dbname: str) -> None:
    admin = create_engine(_admin_dsn(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        # Kick any lingering connections held by an earlier alembic
        # subprocess before the DROP. Subprocess exit should close
        # them, but Postgres can lag briefly.
        conn.execute(sa.text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = :db AND pid <> pg_backend_pid()"
        ), {"db": dbname})
        conn.execute(sa.text(f"DROP DATABASE IF EXISTS {dbname}"))
    admin.dispose()


def _alembic(dbname: str, args: list[str], env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Run `alembic <args>` against `dbname` and return the completed process.

    Returncode != 0 is expected in the refuse cases; caller inspects stderr.
    """
    env = os.environ.copy()
    env["ALEMBIC_DATABASE_URL"] = _dsn(dbname)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["alembic", *args],
        cwd=_API_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# Seed helpers — one per guard. Each inserts the smallest row that
# triggers the specific check.
# ---------------------------------------------------------------------------


def _sql(dbname: str, statements: list[str]) -> None:
    engine = create_engine(_dsn(dbname, sync=True))
    with engine.begin() as conn:
        for s in statements:
            conn.execute(sa.text(s))
    engine.dispose()


def _seed_tenant(dbname: str, extra: dict[str, str] | None = None) -> str:
    """Insert one minimally-valid tenant, return its id.

    Schema-aware: some tenant columns are added by later migrations
    (webhook_secret, email_digest, email_recipients) and don't exist
    at every test target. We introspect `information_schema` and only
    supply the columns the current schema actually has.
    """
    tid = str(uuid.uuid4())
    engine = create_engine(_dsn(dbname, sync=True))
    with engine.connect() as conn:
        existing = {
            row[0]
            for row in conn.execute(sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'tenants'"
            )).fetchall()
        }
    engine.dispose()

    all_cols = {
        "id": f"'{tid}'::uuid",
        "name": "'guard-test'",
        "market": "'ZM'",
        "factor_set": "'CUSTOM'",
        "plan": "'PILOT'",
        "is_active": "true",
        "alert_threshold": "0.2",
        "webhook_secret": "'x'",
        "email_digest": "'OFF'",
        "email_recipients": "'{}'",
    }
    cols = {k: v for k, v in all_cols.items() if k in existing}
    if extra:
        # Callers may specify columns unconditionally; filter those too so
        # a caller pointing at an early revision doesn't crash on a
        # column that doesn't exist yet.
        cols.update({k: v for k, v in extra.items() if k in existing or k == "id"})

    _sql(dbname, [
        f"INSERT INTO tenants ({', '.join(cols.keys())}) "
        f"VALUES ({', '.join(cols.values())})"
    ])
    return tid


# ---------------------------------------------------------------------------
# Guard cases
# ---------------------------------------------------------------------------

# Format: (revision, guard_phrase, upgrade_to, seed_fn, ack_env)
#
# - revision       : the migration whose guard we're testing
# - guard_phrase   : substring that must appear in the refusal message
# - upgrade_to     : how far to upgrade before seeding (must be at or past
#                    the migration under test, so its tables/columns exist)
# - seed_fn        : callable(dbname) that inserts the triggering row
# - ack_env        : env-var name whose value should be the revision
#                    to bypass the guard (None → precondition, unbypassable)
_CASES = [
    (
        "7e2c8ab391f5",
        "api_keys",
        "head",
        lambda db: (
            _seed_tenant(db, extra={"id": "'22222222-2222-2222-2222-222222222222'::uuid"}),
            _sql(db, [
                "INSERT INTO api_keys (id, tenant_id, lookup_id, key_hash, "
                "key_prefix, label, is_active) VALUES "
                "(gen_random_uuid(), '22222222-2222-2222-2222-222222222222'::uuid, "
                "'aaa000bbb111', 'x', 'pk_test_aaa000bbb111', 'guard-test', true)"
            ]),
        ),
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
    (
        "52f6a4d1b0c9",
        "factor_weight",
        "head",
        lambda db: (
            _seed_tenant(db, extra={"id": "'33333333-3333-3333-3333-333333333333'::uuid"}),
            _sql(db, [
                "INSERT INTO factor_weights (id, tenant_id, collection_method, "
                "factor_name, weight, updated_at) VALUES "
                "(gen_random_uuid(), '33333333-3333-3333-3333-333333333333'::uuid, "
                "'PAYROLL', 'threshold_headroom', 0.5, now())"
            ]),
        ),
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
    (
        "5b17a75fd7b3",
        # H8's own downgrade doesn't refuse — it PRESERVES data. Its ack
        # phrase is never emitted; we assert a different thing (round-trip
        # preservation) below in test_h8_preserves_webhook_secret.
        None,
        None,
        None,
        None,
    ),
    (
        "af259bfe8cfa",
        "email_recipients",
        "af259bfe8cfa",
        lambda db: _seed_tenant(db, extra={
            "email_digest": "'DAILY'",
            "email_recipients": "'{\"ops@x.com\"}'",
        }),
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
    (
        "66d275afe3ed",
        "backtest_runs",
        "66d275afe3ed",
        lambda db: (
            _seed_tenant(db, extra={"id": "'44444444-4444-4444-4444-444444444444'::uuid"}),
            _sql(db, [
                "INSERT INTO backtest_runs (id, tenant_id, name, status, "
                "total_collections, factor_set_used, weights_used, started_at, "
                "created_at) VALUES "
                "(gen_random_uuid(), '44444444-4444-4444-4444-444444444444'::uuid, "
                "'guard-test', 'COMPLETED', 0, 'CARD_DEBIT', '{}'::jsonb, "
                "now(), now())"
            ]),
        ),
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
    (
        "ad96b9835926",
        "notifications",
        "ad96b9835926",
        lambda db: (
            _seed_tenant(db, extra={"id": "'55555555-5555-5555-5555-555555555555'::uuid"}),
            _sql(db, [
                "INSERT INTO notifications (id, tenant_id, category, severity, "
                "event_type, title, message, is_read, created_at) VALUES "
                "(gen_random_uuid(), '55555555-5555-5555-5555-555555555555'::uuid, "
                "'SYSTEM', 'INFO', 'test', 'Test', 'Test message', false, now())"
            ]),
        ),
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
    (
        "9ce5ceb0356c",
        "recommended_score",
        "9ce5ceb0356c",
        lambda db: (
            _seed_tenant(db, extra={"id": "'66666666-6666-6666-6666-666666666666'::uuid"}),
            _sql(db, [
                "INSERT INTO score_requests (id, tenant_id, external_customer_id, "
                "external_collection_id, collection_amount, collection_currency, "
                "collection_due_date, collection_method, request_payload) VALUES "
                "('77777777-7777-7777-7777-777777777777'::uuid, "
                "'66666666-6666-6666-6666-666666666666'::uuid, 'c1', 'col1', "
                "500, 'ZAR', '2026-09-15', 'CARD', '{}'::jsonb)",
                "INSERT INTO score_results (id, score_request_id, tenant_id, "
                "score, risk_level, factors, recommended_action, model_version, "
                "scoring_duration_ms, recommended_score) VALUES "
                "(gen_random_uuid(), '77777777-7777-7777-7777-777777777777'::uuid, "
                "'66666666-6666-6666-6666-666666666666'::uuid, 0.5, 'MEDIUM', "
                "'{}'::jsonb, 'collect_normally', 'heuristic_card_v1', 1, 0.3)",
            ]),
        ),
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
    (
        "f012f11380b2",
        "customer data",
        "head",
        _seed_tenant,
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
    (
        "45bde65cbdd7",  # H7 — precondition, no bypass
        "reclassify",
        "8f4a1c2d0e3b",
        lambda db: _seed_tenant(db, extra={"factor_set": "'PAYROLL'"}),
        None,  # None → unbypassable
    ),
    (
        "c9a7f10e5b28",  # bulk_scoring_jobs table
        "bulk-scoring history",
        "c9a7f10e5b28",
        lambda db: (
            _seed_tenant(db, extra={"id": "'99999999-9999-9999-9999-999999999999'::uuid"}),
            _sql(db, [
                "INSERT INTO bulk_scoring_jobs (id, tenant_id, job_id, "
                "status, total_items, completed_items) VALUES "
                "(gen_random_uuid(), '99999999-9999-9999-9999-999999999999'::uuid, "
                "gen_random_uuid(), 'completed', 5, 5)"
            ]),
        ),
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
    (
        "d4e8c1f95a72",  # weight_change_log + score_results.weights_snapshot
        "weight-tuning audit trail",
        "d4e8c1f95a72",
        lambda db: (
            _seed_tenant(db, extra={"id": "'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid"}),
            _sql(db, [
                "INSERT INTO weight_change_log (id, tenant_id, "
                "collection_method, factor_name, old_weight, new_weight, "
                "actor_type, actor_name, changed_at) VALUES "
                "(gen_random_uuid(), 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, "
                "'CARD', 'card_health', 0.10, 0.15, 'user', 'seed', now())"
            ]),
        ),
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
    (
        "f3b7d92a1c8e",  # activity_log + outcomes soft-delete
        "audit trail for team",
        "f3b7d92a1c8e",
        lambda db: (
            _seed_tenant(db, extra={"id": "'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid"}),
            _sql(db, [
                "INSERT INTO activity_log (id, tenant_id, entity_type, "
                "action, actor_type, actor_name, created_at) VALUES "
                "(gen_random_uuid(), 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, "
                "'user', 'update', 'user', 'seed', now())"
            ]),
        ),
        "FORCE_DESTRUCTIVE_DOWNGRADE",
    ),
]


@pytest.mark.parametrize(
    "revision,phrase,upgrade_to,seed_fn,ack_env",
    [c for c in _CASES if c[1] is not None],
    ids=lambda x: x if isinstance(x, str) else "-",
)
def test_guard_refuses_without_ack(revision, phrase, upgrade_to, seed_fn, ack_env):
    """Seed the triggering row, run downgrade with no ack, expect refusal."""
    dbname = f"paypredict_guard_{revision[:8]}"
    _create_fresh_db(dbname)
    try:
        result = _alembic(
            dbname, ["upgrade", upgrade_to],
            env_extra={"FORCE_DESTRUCTIVE_UPGRADE": "all"},
        )
        assert result.returncode == 0, (
            f"upgrade to {upgrade_to} failed:\n{result.stderr}"
        )

        seed_fn(dbname)

        # Downgrade to just before this revision — that's the step whose
        # guard we're testing. alembic supports "revision-1" syntax for
        # "one before this".
        result = _alembic(dbname, ["downgrade", f"{revision}-1"])
        assert result.returncode != 0, (
            f"expected downgrade to REFUSE but it succeeded:\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
        assert phrase in result.stderr, (
            f"expected guard message to contain {phrase!r}\nstderr={result.stderr}"
        )
    finally:
        _drop_db(dbname)


@pytest.mark.parametrize(
    "revision,phrase,upgrade_to,seed_fn,ack_env",
    [c for c in _CASES if c[4] is not None and c[1] is not None],
    ids=lambda x: x if isinstance(x, str) else "-",
)
def test_guard_proceeds_with_correct_ack(revision, phrase, upgrade_to, seed_fn, ack_env):
    """Same setup, but with the ack env var set to this revision, the
    downgrade proceeds. Precondition-only guards (ack_env=None) are
    filtered out — they don't have a bypass path by design."""
    dbname = f"paypredict_guard_ack_{revision[:8]}"
    _create_fresh_db(dbname)
    try:
        result = _alembic(
            dbname, ["upgrade", upgrade_to],
            env_extra={"FORCE_DESTRUCTIVE_UPGRADE": "all"},
        )
        assert result.returncode == 0, (
            f"upgrade to {upgrade_to} failed:\n{result.stderr}"
        )

        seed_fn(dbname)

        result = _alembic(
            dbname, ["downgrade", f"{revision}-1"],
            env_extra={ack_env: revision},
        )
        assert result.returncode == 0, (
            f"expected downgrade with ack={ack_env}={revision} to succeed, "
            f"got failure:\n{result.stderr}"
        )
    finally:
        _drop_db(dbname)


def test_h8_preserves_webhook_secret_across_round_trip():
    """H8's real guarantee: down + up preserves the ORIGINAL secret per
    tenant so customers' cached HMAC keys survive an emergency rollback +
    redeploy. Distinct from the refuse/ack shape of every other guard."""
    dbname = "paypredict_guard_h8"
    _create_fresh_db(dbname)
    try:
        r = _alembic(
            dbname, ["upgrade", "5b17a75fd7b3"],
            env_extra={"FORCE_DESTRUCTIVE_UPGRADE": "all"},
        )
        assert r.returncode == 0, r.stderr

        tenant_id = "88888888-8888-8888-8888-888888888888"
        original = "whsec_ORIGINAL_CACHED_BY_CUSTOMER"
        _sql(dbname, [
            f"INSERT INTO tenants (id, name, market, factor_set, plan, "
            f"is_active, alert_threshold, webhook_secret, email_recipients) VALUES "
            f"('{tenant_id}'::uuid, 'preserve-me', 'ZM', 'CUSTOM', 'PILOT', "
            f"true, 0.2, '{original}', '{{}}')"
        ])

        # Downgrade past H8 (stashes the secret) then upgrade back
        # (restores it, drops the preservation table).
        r = _alembic(
            dbname, ["downgrade", "ad96b9835926"],
            env_extra={"FORCE_DESTRUCTIVE_DOWNGRADE": "all"},
        )
        assert r.returncode == 0, r.stderr

        r = _alembic(
            dbname, ["upgrade", "5b17a75fd7b3"],
            env_extra={"FORCE_DESTRUCTIVE_UPGRADE": "all"},
        )
        assert r.returncode == 0, r.stderr

        engine = create_engine(_dsn(dbname, sync=True))
        with engine.connect() as conn:
            after = conn.execute(sa.text(
                f"SELECT webhook_secret FROM tenants WHERE id = '{tenant_id}'::uuid"
            )).scalar_one()
            table_exists = conn.execute(sa.text(
                "SELECT to_regclass('_preserved_webhook_secrets')"
            )).scalar_one()
        engine.dispose()

        assert after == original, (
            f"H8 preservation FAILED: secret changed. before={original!r} "
            f"after={after!r}"
        )
        assert table_exists is None, (
            "preservation table should be cleaned up on re-upgrade"
        )
    finally:
        _drop_db(dbname)
