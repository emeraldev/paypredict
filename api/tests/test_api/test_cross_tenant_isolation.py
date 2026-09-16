"""Regression guard for cross-tenant data leaks on the JWT dashboard surface.

Isolation between tenants is enforced today entirely at the application
layer: every service method takes a `tenant_id` and adds it to the SQL
WHERE clause. A missed WHERE in a future service = cross-tenant leak
with no database backstop. Postgres RLS is on the roadmap but not yet
active (see `context/launch-roadmap.md`); until it is, this test file
IS the backstop.

Shape: seed two tenants (A and B) with one row in every tenant-scoped
table, log in as A's admin, then hit every dashboard read/write and
assert none of B's rows or ids appear. Each endpoint is its own
parametrized case so a leak surfaces as a named failure in CI rather
than a single opaque "cross-tenant test failed" line.

When adding a new dashboard endpoint that returns tenant-scoped data,
add it to `LIST_CASES`, `SINGLETON_ENDPOINTS`, `DETAIL_404_CASES`, or
`WRITE_404_CASES` as appropriate. That single line is what makes this
test a permanent guard.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityActorType, ActivityLog
from app.models.alert import Alert, AlertType
from app.models.api_key import ApiKey
from app.models.backtest import BacktestRun, BacktestStatus
from app.models.factor_weight import FactorWeight
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
)
from app.models.outcome import Outcome, OutcomeStatus
from app.models.score_request import (
    CollectionCurrency,
    CollectionMethod,
    ScoreRequest,
)
from app.models.score_result import RiskLevel, ScoreResult
from app.models.tenant import FactorSet, Market, Plan, Tenant
from app.models.user import User, UserRole
from app.models.weight_change_log import WeightChangeActorType, WeightChangeLog
from app.scoring.registry import get_default_weights_for_method
from app.services.auth_service import hash_password


@dataclass
class SeededTenant:
    """Bundle of every id that response bodies for THIS tenant may
    contain, plus the JWT once the fixture has logged in.

    `all_ids` returns the union as strings. The leak checks assert
    that none of B's `all_ids` appear anywhere in A's response bodies
    (and vice versa).
    """

    tenant: Tenant
    admin_email: str
    admin_password: str
    admin_user_id: uuid.UUID
    api_key_id: uuid.UUID
    score_request_id: uuid.UUID
    score_result_id: uuid.UUID
    customer_id: str
    collection_id: str
    outcome_id: uuid.UUID
    alert_id: uuid.UUID
    notification_id: uuid.UUID
    backtest_run_id: uuid.UUID
    weight_change_log_id: uuid.UUID
    activity_log_id: uuid.UUID
    token: str | None = None

    @property
    def all_ids(self) -> set[str]:
        return {
            str(self.tenant.id),
            str(self.admin_user_id),
            str(self.api_key_id),
            str(self.score_request_id),
            str(self.score_result_id),
            self.customer_id,
            self.collection_id,
            str(self.outcome_id),
            str(self.alert_id),
            str(self.notification_id),
            str(self.backtest_run_id),
            str(self.weight_change_log_id),
            str(self.activity_log_id),
        }


async def _seed_tenant_with_full_data(
    db: AsyncSession, label: str
) -> SeededTenant:
    """Create a tenant and one row per tenant-scoped table.

    `label` is embedded verbatim in string columns so any leak names
    the offending tenant in the assertion diff.
    """
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"Xtenant test {label}",
        market=Market.ZM,
        factor_set=FactorSet.CARD_DEBIT,
        plan=Plan.STARTER,
        is_active=True,
        alert_threshold=0.20,
        webhook_secret=f"whsec_xtenant_{label.lower()}",
    )
    db.add(tenant)

    api_key = ApiKey(
        tenant_id=tenant.id,
        # lookup_id must be unique + short — this test never authenticates
        # by API key, so any distinct value works.
        lookup_id=f"xt_lookup_{label.lower()}",
        key_hash=f"$2b$12$xtenant_{label.lower()}_hash_placeholder_padding_ok_",
        key_prefix=f"pk_xt_{label.lower()}",
        label=f"Xtenant {label} Key",
        is_active=True,
    )
    db.add(api_key)

    for method in (CollectionMethod.CARD, CollectionMethod.DEBIT_ORDER):
        for factor_name, weight in get_default_weights_for_method(method).items():
            db.add(
                FactorWeight(
                    tenant_id=tenant.id,
                    collection_method=method.value,
                    factor_name=factor_name,
                    weight=weight,
                )
            )

    now = datetime.now(timezone.utc)
    admin_email = f"admin+xt-{label.lower()}@paypredict.test"
    admin_password = "Xtenant-Test-Pass-1"
    admin = User(
        tenant_id=tenant.id,
        email=admin_email,
        name=f"Xtenant {label} Admin",
        password_hash=hash_password(admin_password),
        role=UserRole.ADMIN,
        # Stamp so the JWT iat check has a real timestamp to compare against.
        password_changed_at=now,
    )
    db.add(admin)
    await db.flush()

    customer_id = f"XT_{label}_CUST_1"
    collection_id = f"XT_{label}_COL_1"
    score_req = ScoreRequest(
        tenant_id=tenant.id,
        external_customer_id=customer_id,
        external_collection_id=collection_id,
        collection_amount=Decimal("1500.00"),
        collection_currency=CollectionCurrency.ZMW,
        collection_due_date=date.today() + timedelta(days=7),
        collection_method=CollectionMethod.CARD,
        request_payload={"total_payments": 10, "successful_payments": 8},
    )
    db.add(score_req)
    await db.flush()

    score_res = ScoreResult(
        score_request_id=score_req.id,
        tenant_id=tenant.id,
        score=0.42,
        risk_level=RiskLevel.MEDIUM,
        factors={"evaluated": [], "skipped": []},
        recommended_action="collect_normally",
        model_version="heuristic_card_v1",
        scoring_duration_ms=1,
    )
    db.add(score_res)
    await db.flush()

    outcome = Outcome(
        score_result_id=score_res.id,
        tenant_id=tenant.id,
        external_collection_id=collection_id,
        outcome=OutcomeStatus.SUCCESS,
        amount_collected=Decimal("1500.00"),
        attempted_at=now,
        reported_at=now,
    )
    db.add(outcome)

    alert = Alert(
        tenant_id=tenant.id,
        alert_type=AlertType.HIGH_RISK_BATCH,
        message=f"XT_{label}_ALERT_MESSAGE",
        metadata_={},
        is_read=False,
    )
    db.add(alert)

    notif = Notification(
        tenant_id=tenant.id,
        category=NotificationCategory.SYSTEM,
        severity=NotificationSeverity.INFO,
        event_type="test_event",
        title=f"XT_{label}_NOTIF_TITLE",
        message=f"XT_{label}_NOTIF_MSG",
        is_read=False,
    )
    db.add(notif)

    backtest_run = BacktestRun(
        tenant_id=tenant.id,
        name=f"XT {label} Run",
        status=BacktestStatus.COMPLETED,
        total_collections=1,
        factor_set_used=FactorSet.CARD_DEBIT.value,
        weights_used={"card_health": 0.10},
        summary={},
        confusion_matrix={},
        top_failure_factors=[],
        started_at=now,
        completed_at=now,
    )
    db.add(backtest_run)

    weight_log = WeightChangeLog(
        tenant_id=tenant.id,
        collection_method=CollectionMethod.CARD.value,
        factor_name="card_health",
        old_weight=0.10,
        new_weight=0.15,
        actor_type=WeightChangeActorType.USER,
        actor_id=admin.id,
        actor_name=admin.name,
        context="upsert",
    )
    db.add(weight_log)

    activity_log = ActivityLog(
        tenant_id=tenant.id,
        entity_type="user",
        entity_id=admin.id,
        action="create",
        before=None,
        after={"email": admin.email},
        actor_type=ActivityActorType.USER,
        actor_id=admin.id,
        actor_name=admin.name,
        context=None,
    )
    db.add(activity_log)
    await db.flush()

    return SeededTenant(
        tenant=tenant,
        admin_email=admin_email,
        admin_password=admin_password,
        admin_user_id=admin.id,
        api_key_id=api_key.id,
        score_request_id=score_req.id,
        score_result_id=score_res.id,
        customer_id=customer_id,
        collection_id=collection_id,
        outcome_id=outcome.id,
        alert_id=alert.id,
        notification_id=notif.id,
        backtest_run_id=backtest_run.id,
        weight_change_log_id=weight_log.id,
        activity_log_id=activity_log.id,
    )


async def _login(async_client, email: str, password: str) -> str:
    r = await async_client.post(
        "/v1/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, f"login failed for {email}: {r.text}"
    return r.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def two_tenants(db_session: AsyncSession, async_client):
    """A and B, each with parallel data across every tenant-scoped table.

    A's JWT is what every test uses; B's `all_ids` are the haystack
    each leak-check scans for.
    """
    a = await _seed_tenant_with_full_data(db_session, "A")
    b = await _seed_tenant_with_full_data(db_session, "B")
    a.token = await _login(async_client, a.admin_email, a.admin_password)
    return a, b


# ---- List endpoints ----------------------------------------------------
#
# For each `path`, the response's `items` list must NOT contain any of
# B's ids in `id_fields`. This catches the classic missed-WHERE bug on
# any dashboard read that pages over tenant-scoped rows.

LIST_CASES = [
    # (path, id_fields_to_check_on_each_item, expected_a_id_attr)
    # `expected_a_id_attr` names an attribute on SeededTenant whose
    # stringified value MUST appear in A's response — a sanity check
    # against a false-pass where the endpoint returns an empty list.
    # A separate "None" sentinel means we don't have a stable id to
    # check for (e.g. the weight-change log's id is generated during
    # seed but not surfaced back through the schema in a predictable
    # place); rely on len(items) >= 1 instead.
    ("/v1/scores", ("score_id", "customer_id", "collection_id"), "score_result_id"),
    ("/v1/outcomes", ("outcome_id", "collection_id"), "outcome_id"),
    ("/v1/config/api-keys", ("id",), "api_key_id"),
    ("/v1/config/team", ("id", "email"), "admin_user_id"),
    ("/v1/config/weights/history", ("id",), "weight_change_log_id"),
    ("/v1/config/activity", ("id",), "activity_log_id"),
    ("/v1/backtests", ("backtest_id", "name"), "backtest_run_id"),
    ("/v1/notifications", ("id", "title", "message"), "notification_id"),
    ("/v1/alerts", ("id", "message"), "alert_id"),
]


@pytest.mark.parametrize(
    "path, id_fields, expected_a_id_attr",
    LIST_CASES,
    ids=[c[0] for c in LIST_CASES],
)
@pytest.mark.asyncio
async def test_list_endpoint_returns_no_other_tenant_rows(
    async_client, two_tenants, path, id_fields, expected_a_id_attr
):
    a, b = two_tenants
    r = await async_client.get(path, headers=_auth(a.token))
    assert r.status_code == 200, f"{path}: {r.text}"
    body = r.json()
    items = body["items"] if isinstance(body, dict) and "items" in body else body
    assert isinstance(items, list), (
        f"{path}: expected list-shaped response, got {type(items).__name__}"
    )
    # Sanity check: A must actually see her own seeded row, otherwise
    # the leak-check below passes vacuously on an empty list.
    a_expected_id = str(getattr(a, expected_a_id_attr))
    body_str = r.text
    assert a_expected_id in body_str, (
        f"{path}: tenant A cannot see her own row {a_expected_id} — "
        f"the leak check below would pass vacuously"
    )
    for item in items:
        for field_name in id_fields:
            value = item.get(field_name)
            if value is None:
                continue
            assert str(value) not in b.all_ids, (
                f"{path} leaked tenant B row via '{field_name}' = {value!r}"
            )


# ---- Singleton response endpoints --------------------------------------
#
# These return a single record (weights bundle, alerts config,
# analytics summary, ...). The full response body must not mention any
# of B's ids anywhere. Cheap text-scan; catches leaks that would
# embed a foreign row (e.g. analytics aggregating across tenants).

SINGLETON_ENDPOINTS = [
    "/v1/config/weights",
    "/v1/config/alerts",
    "/v1/analytics/summary?period=30d",
    "/v1/analytics/collection-rate?period=30d",
    "/v1/analytics/factors?period=30d",
    "/v1/analytics/accuracy?period=30d",
]


@pytest.mark.parametrize("path", SINGLETON_ENDPOINTS)
@pytest.mark.asyncio
async def test_singleton_endpoint_scoped_to_caller_tenant(
    async_client, two_tenants, path
):
    a, b = two_tenants
    r = await async_client.get(path, headers=_auth(a.token))
    assert r.status_code == 200, f"{path}: {r.text}"
    body_str = r.text
    for b_id in b.all_ids:
        assert b_id not in body_str, (
            f"{path} response contained tenant B id {b_id!r}"
        )


# ---- Detail-by-id endpoints (must 404 for another tenant's id) ---------

DETAIL_404_CASES = [
    # (path_template, attribute on SeededTenant holding B's id)
    ("/v1/scores/{id}", "score_result_id"),
    ("/v1/backtest/{id}", "backtest_run_id"),
]


@pytest.mark.parametrize(
    "template, b_field",
    DETAIL_404_CASES,
    ids=[c[0] for c in DETAIL_404_CASES],
)
@pytest.mark.asyncio
async def test_detail_by_id_returns_404_for_other_tenant(
    async_client, two_tenants, template, b_field
):
    a, b = two_tenants
    url = template.format(id=getattr(b, b_field))
    r = await async_client.get(url, headers=_auth(a.token))
    assert r.status_code == 404, (
        f"expected 404 for cross-tenant GET {url}, got {r.status_code}: {r.text[:200]}"
    )


# ---- Write-by-id endpoints (must 404 for another tenant's id) ----------
#
# The mirror class of bug: a mutation that resolves a resource by id
# and forgets to include tenant_id in the WHERE. Prevents "you can
# delete their API key by knowing its UUID."

WRITE_404_CASES = [
    # (method, path_template, b_attr, body)
    ("PATCH", "/v1/config/team/{id}", "admin_user_id", {"role": "VIEWER"}),
    ("DELETE", "/v1/config/team/{id}", "admin_user_id", None),
    ("PATCH", "/v1/config/api-keys/{id}", "api_key_id", {"is_active": False}),
    ("DELETE", "/v1/config/api-keys/{id}", "api_key_id", None),
    ("PATCH", "/v1/notifications/{id}/read", "notification_id", None),
    ("PATCH", "/v1/alerts/{id}/read", "alert_id", None),
]


@pytest.mark.parametrize(
    "method, template, b_field, body",
    WRITE_404_CASES,
    ids=[f"{c[0]} {c[1]}" for c in WRITE_404_CASES],
)
@pytest.mark.asyncio
async def test_write_by_id_returns_404_for_other_tenant(
    async_client, two_tenants, method, template, b_field, body
):
    a, b = two_tenants
    url = template.format(id=getattr(b, b_field))
    if method == "PATCH":
        r = await async_client.patch(url, headers=_auth(a.token), json=body or {})
    elif method == "DELETE":
        r = await async_client.delete(url, headers=_auth(a.token))
    else:
        pytest.fail(f"unhandled method {method!r}")
    assert r.status_code == 404, (
        f"expected 404 for cross-tenant {method} {url}, got {r.status_code}: {r.text[:200]}"
    )


# ---- Counter endpoint (leak would surface as inflated count) -----------


@pytest.mark.asyncio
async def test_unread_count_counts_only_caller_tenant(
    async_client, two_tenants
):
    """`/v1/notifications/unread-count` returns a scalar count, so
    the "no B ids in body" check can't apply. Instead we assert the
    number: each fixture seeded exactly one unread notification; A's
    endpoint must return 1 (not 2)."""
    a, _b = two_tenants
    r = await async_client.get(
        "/v1/notifications/unread-count", headers=_auth(a.token)
    )
    assert r.status_code == 200, r.text
    assert r.json()["unread_count"] == 1, (
        f"unread-count leaked B's notification into A's count: {r.json()}"
    )
