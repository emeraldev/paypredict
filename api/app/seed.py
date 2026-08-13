"""Seed script for local development and demos.

Creates:
- 2 tenants (SA + ZM) with API keys and default factor weights
- 2 admin users + 2 viewer users (for team management demo)
- 60 scored collections (40 SA + 20 ZM) with real factor breakdowns
- Outcomes for ~80% of scores (mix of SUCCESS/FAILED)
- Prints login credentials and API keys when done

Usage: python -m app.seed
"""

import argparse
import asyncio
import random
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import bcrypt
from sqlalchemy import select, text

from app.database import async_session
from app.models.api_key import ApiKey
from app.models.factor_weight import FactorWeight
from app.models.outcome import FailureCategory, Outcome, OutcomeStatus
from app.models.score_request import CollectionCurrency, CollectionMethod, ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.models.alert import Alert, AlertType
from app.models.backtest import BacktestItem, BacktestRun, BacktestStatus
from app.models.notification import Notification, NotificationCategory, NotificationSeverity
from app.models.tenant import FactorSet, Market, Plan, Tenant
from app.models.user import User, UserRole
from app.scoring.engine import ScoringEngine
from app.scoring.registry import get_default_weights, get_default_weights_for_method
from app.scoring.timing_optimiser import optimise_collection_date
from app.services.api_key_service import mint_key
from app.services.auth_service import hash_password


def generate_api_key(env_prefix: str) -> tuple[str, str, str, str]:
    """Generate an API key and return (raw_key, hashed_key, lookup_id, display_prefix).

    Uses the shared `mint_key` so seed keys have the same shape the
    dashboard mints — an integration test smoke against a seeded key
    exercises the real auth path.
    """
    raw, lookup_id, display_prefix = mint_key(env_prefix)
    hashed = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return raw, hashed, lookup_id, display_prefix


# ---- Customer data templates ----

def _sa_customer(rng: random.Random, risk_bias: str) -> dict:
    """Generate realistic SA card customer data with controllable risk bias."""
    if risk_bias == "high":
        total, success = rng.randint(8, 20), rng.randint(2, 5)
        card_type = rng.choice(["debit", "debit", "credit"])
        salary_day = rng.choice([25, 26, 27, 28, 15])
        days_since = rng.randint(30, 90)
    elif risk_bias == "medium":
        total, success = rng.randint(6, 15), rng.randint(4, 8)
        card_type = rng.choice(["debit", "credit"])
        salary_day = rng.choice([25, 26, 27])
        days_since = rng.randint(10, 30)
    else:
        total, success = rng.randint(8, 20), rng.randint(7, 18)
        card_type = rng.choice(["credit", "debit"])
        salary_day = 25
        days_since = rng.randint(1, 10)

    last_payment = (datetime.now(timezone.utc) - timedelta(days=days_since)).date()
    instalment_num = rng.randint(1, 6)
    total_instalments = rng.choice([3, 4, 6, 12])
    if instalment_num > total_instalments:
        instalment_num = total_instalments

    return {
        "total_payments": total,
        "successful_payments": min(success, total),
        "last_successful_payment_date": last_payment.isoformat(),
        "average_collection_amount": round(rng.uniform(500, 5000), 2),
        "instalment_number": instalment_num,
        "total_instalments": total_instalments,
        "card_type": card_type,
        "card_expiry_date": (datetime.now(timezone.utc) + timedelta(days=rng.randint(60, 900))).date().isoformat(),
        "known_salary_day": salary_day,
    }


def _payroll_customer(rng: random.Random, risk_bias: str, segment: str) -> dict:
    """Generate realistic payroll-deduction customer data for Zambia
    salary-advance lenders. `segment` is one of "government" or "mining"
    (matches Lumo's actual mix). Threshold headroom is the dominant risk
    driver, so we synthesise gross_salary + current_total_deductions such
    that the resulting ratio matches the requested risk bias."""

    if segment == "government":
        gross = round(rng.uniform(6000, 15000), 2)  # ZMW, reasonable civil-service range
    else:  # mining
        gross = round(rng.uniform(8000, 22000), 2)  # miners earn more but volatile

    # Existing deductions from other creditors as % of 40% ceiling
    if risk_bias == "high":
        deduction_pct_of_cap = rng.uniform(0.80, 0.98)
        total = rng.randint(3, 12)
        success = rng.randint(0, total // 2)
        resubmissions = rng.randint(2, 5)
    elif risk_bias == "medium":
        deduction_pct_of_cap = rng.uniform(0.55, 0.80)
        total = rng.randint(3, 10)
        success = rng.randint(total // 2, total - 1)
        resubmissions = rng.randint(0, 2)
    else:  # low
        deduction_pct_of_cap = rng.uniform(0.15, 0.50)
        total = rng.randint(3, 12)
        success = max(rng.randint(total - 2, total), 0)
        resubmissions = 0

    current_deductions = round(gross * 0.40 * deduction_pct_of_cap, 2)
    net_pay = round(gross - current_deductions - (gross * 0.15), 2)  # rough tax proxy
    active_loans = rng.randint(1, 4) if risk_bias != "low" else rng.choice([1, 2])

    total_instalments = rng.choice([1, 2, 3])  # short-term advances
    instalment_num = rng.randint(1, total_instalments)

    return {
        "total_payments": total,
        "successful_payments": min(success, total),
        "instalment_number": instalment_num,
        "total_instalments": total_instalments,
        "active_loan_count": active_loans,
        "loans_taken_last_90d": rng.randint(0, 3),
        # PAYROLL-specific
        "gross_salary": gross,
        "net_pay": net_pay,
        "current_total_deductions": current_deductions,
        "deduction_threshold_pct": 0.40,  # Zambia
        "resubmission_count": resubmissions,
        "borrower_segment": segment,
    }


def _zm_customer(rng: random.Random, risk_bias: str) -> dict:
    """Generate realistic ZM mobile money customer data."""
    if risk_bias == "high":
        bal_avg, bal_cur = rng.uniform(50, 200), rng.uniform(10, 80)
        hours_inflow = rng.randint(72, 200)
        active_loans = rng.randint(2, 5)
    elif risk_bias == "medium":
        bal_avg, bal_cur = rng.uniform(200, 600), rng.uniform(100, 400)
        hours_inflow = rng.randint(24, 72)
        active_loans = rng.randint(1, 3)
    else:
        bal_avg, bal_cur = rng.uniform(500, 2000), rng.uniform(400, 1500)
        hours_inflow = rng.randint(2, 24)
        active_loans = rng.choice([0, 1])

    total = rng.randint(5, 20)
    success = min(rng.randint(3, total), total)

    return {
        "total_payments": total,
        "successful_payments": success,
        "wallet_balance_7d_avg": round(bal_avg, 2),
        "wallet_balance_current": round(bal_cur, 2),
        "hours_since_last_inflow": hours_inflow,
        "regular_inflow_day": rng.choice(["monday", "friday", "wednesday"]),
        "active_loan_count": active_loans,
        "transactions_last_7d": rng.randint(3, 25),
        "transactions_avg_7d": rng.randint(8, 20),
        "last_airtime_purchase_days_ago": rng.randint(0, 14),
        "loans_taken_last_90d": rng.randint(0, 4),
        "instalment_number": rng.randint(1, 4),
        "total_instalments": rng.choice([3, 4, 6]),
    }


FAILURE_REASONS = [
    ("insufficient_funds", FailureCategory.SOFT_DECLINE),
    ("do_not_honour", FailureCategory.SOFT_DECLINE),
    ("general_decline", FailureCategory.SOFT_DECLINE),
    ("card_cancelled", FailureCategory.HARD_DECLINE),
    ("account_closed", FailureCategory.HARD_DECLINE),
    ("timeout", FailureCategory.TECHNICAL),
]


# ---- Loan-journey generator ----

def _pattern_outcomes(pattern: str, n: int, rng: random.Random) -> list[str | None]:
    """Emit outcome states per instalment for one of the demo loan patterns.

    None = "no outcome reported yet" (the row still gets a score but no
    Outcome). Matches the real-world state where later instalments in
    an active loan haven't been attempted yet.
    """
    if pattern == "all_success":
        return ["SUCCESS"] * n
    if pattern == "late_default":
        # Perfect record until the last instalment defaults — the
        # "everything looked fine and then it didn't" pattern.
        return ["SUCCESS"] * (n - 1) + ["FAILED"]
    if pattern == "mid_default":
        # 2 SUCCESS then a run of FAILED — the "paid twice then went
        # silent" persona.
        k = min(2, max(1, n - 1))
        return ["SUCCESS"] * k + ["FAILED"] * (n - k)
    if pattern == "early_default":
        # First attempt fails; subsequent ones mixed (partial recovery).
        rest = rng.choices(["SUCCESS", "FAILED"], weights=[0.4, 0.6], k=n - 1)
        return ["FAILED"] + rest
    if pattern == "in_progress":
        # First half reported, later ones still pending. Simulates a
        # loan that's mid-way through when the demo is being shown.
        k = (n + 1) // 2
        return ["SUCCESS"] * k + [None] * (n - k)
    return [None] * n


async def _seed_journey_customer(
    *,
    db,
    engine: ScoringEngine,
    tenant: Tenant,
    method: CollectionMethod,
    factor_set: str,
    currency: CollectionCurrency,
    customer_id: str,
    loan_size: int,
    pattern: str,
    base_amount: float,
    customer_template_fn,
    template_kwargs: dict,
    rng: random.Random,
    now: datetime,
    per_instalment_override: dict[int, dict] | None = None,
) -> None:
    """Emit `loan_size` scored collections + outcomes for one customer,
    forming a coherent loan journey.

    Each instalment carries history derived from earlier ones
    (`total_payments`, `successful_payments`,
    `last_successful_payment_date`, `resubmission_count`) — so
    history-aware factors see a real record and scores evolve as
    the customer's track record builds up. Emits its own outcomes
    per `pattern`; do NOT feed these into the generic ~80% outcome
    loop that runs over singleton customers.

    `per_instalment_override` lets named personas (e.g. Lumo's
    "government worker whose deduction breached the 40% cap")
    inject scenario-specific customer_data on the target instalment
    without disturbing the default template.
    """
    outcomes_plan = _pattern_outcomes(pattern, loan_size, rng)
    days_between = 30

    last_success_date: date | None = None
    successful_so_far = 0
    resubs_so_far = 0

    for k in range(1, loan_size + 1):
        scored_at = now - timedelta(
            days=(loan_size - k + 1) * days_between + rng.randint(-3, 3)
        )
        due_date = (scored_at + timedelta(days=rng.randint(3, 7))).date()

        customer_data = customer_template_fn(rng, **template_kwargs)

        # Overlay history derived from prior instalments' outcomes.
        customer_data["total_payments"] = k - 1
        customer_data["successful_payments"] = successful_so_far
        customer_data["resubmission_count"] = resubs_so_far
        customer_data["instalment_number"] = k
        customer_data["total_instalments"] = loan_size
        if last_success_date is not None:
            customer_data["last_successful_payment_date"] = last_success_date.isoformat()

        # Per-instalment override wins over history + template.
        if per_instalment_override and k in per_instalment_override:
            customer_data.update(per_instalment_override[k])

        collection_data = {
            "collection_amount": base_amount,
            "collection_due_date": due_date,
            "collection_method": method.value,
            "collection_currency": currency.value,
        }

        scoring_result = engine.score(
            factor_set=factor_set,
            customer_data=customer_data,
            collection_data=collection_data,
            collection_method=method,
        )
        timing = optimise_collection_date(
            engine,
            customer_data=customer_data,
            collection_data=collection_data,
            collection_method=method,
            original_score=scoring_result.score,
            today=due_date,
        )
        rec_action = (
            "shift_date" if timing.should_shift else scoring_result.recommended_action
        )

        payload = {
            "customer_data": customer_data,
            "collection_amount": base_amount,
            "collection_due_date": due_date.isoformat(),
            "collection_method": method.value,
            "collection_currency": currency.value,
        }

        req = ScoreRequest(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            external_customer_id=customer_id,
            external_collection_id=f"{customer_id}_inst_{k:02d}",
            collection_amount=Decimal(str(base_amount)),
            collection_currency=currency,
            collection_due_date=due_date,
            collection_method=method,
            request_payload=payload,
            created_at=scored_at,
        )
        res = ScoreResult(
            id=uuid.uuid4(),
            score_request_id=req.id,
            tenant_id=tenant.id,
            score=scoring_result.score,
            risk_level=RiskLevel(scoring_result.risk_level),
            factors={
                "evaluated": [
                    {
                        "factor_name": f.factor_name,
                        "raw_score": f.raw_score,
                        "weight": f.weight,
                        "weighted_score": f.weighted_score,
                        "explanation": f.explanation,
                    }
                    for f in scoring_result.factors
                ],
                "skipped": scoring_result.skipped_factors,
            },
            recommended_action=rec_action,
            recommended_collection_date=timing.recommended_date,
            recommended_score=timing.recommended_score,
            score_improvement=(
                timing.score_improvement if timing.should_shift else None
            ),
            model_version=scoring_result.model_version,
            scoring_duration_ms=scoring_result.scoring_duration_ms,
            weights_snapshot=scoring_result.weights_snapshot,
            created_at=scored_at,
        )
        db.add(req)
        db.add(res)

        # Outcome for this instalment (None = still to be attempted).
        outcome_kind = outcomes_plan[k - 1]
        if outcome_kind is not None:
            attempted_dt = datetime(
                due_date.year, due_date.month, due_date.day, 8, 0, tzinfo=timezone.utc
            )
            if outcome_kind == "SUCCESS":
                successful_so_far += 1
                last_success_date = due_date
                db.add(Outcome(
                    id=uuid.uuid4(),
                    score_result_id=res.id,
                    tenant_id=tenant.id,
                    external_collection_id=req.external_collection_id,
                    outcome=OutcomeStatus.SUCCESS,
                    failure_reason=None,
                    failure_category=None,
                    amount_collected=req.collection_amount,
                    attempted_at=attempted_dt,
                    reported_at=attempted_dt + timedelta(hours=rng.randint(1, 24)),
                ))
            else:
                resubs_so_far += 1
                reason, category = rng.choice(FAILURE_REASONS)
                db.add(Outcome(
                    id=uuid.uuid4(),
                    score_result_id=res.id,
                    tenant_id=tenant.id,
                    external_collection_id=req.external_collection_id,
                    outcome=OutcomeStatus.FAILED,
                    failure_reason=reason,
                    failure_category=category,
                    amount_collected=None,
                    attempted_at=attempted_dt,
                    reported_at=attempted_dt + timedelta(hours=rng.randint(1, 24)),
                ))


async def _wipe(db) -> None:
    """Truncate all seed-owned tables. CASCADE follows the tenant FK chain
    through scores, outcomes, alerts, backtests, notifications, etc."""
    await db.execute(text(
        "TRUNCATE "
        "outcomes, score_results, score_requests, "
        "factor_weights, api_keys, notifications, alerts, "
        "backtest_items, backtest_runs, users, tenants "
        "RESTART IDENTITY CASCADE"
    ))
    await db.commit()


async def seed(reseed: bool = False) -> None:
    engine = ScoringEngine()
    rng = random.Random(42)  # Deterministic for reproducible demos

    async with async_session() as db:
        # Check if already seeded
        result = await db.execute(select(Tenant).limit(1))
        if result.scalar_one_or_none():
            if reseed:
                print("Wiping existing seed data...")
                await _wipe(db)
            else:
                print("Database already seeded. Pass --reseed to refresh.")
                return

        now = datetime.now(timezone.utc)

        # ---- Tenants ----
        sa_tenant = Tenant(
            id=uuid.uuid4(),
            name="Demo BNPL SA",
            market=Market.SA,
            factor_set=FactorSet.CARD_DEBIT,
            plan=Plan.STARTER,
            is_active=True,
            alert_threshold=0.20,
            webhook_secret="whsec_" + secrets.token_urlsafe(32),
            created_at=now,
            updated_at=now,
        )
        zm_tenant = Tenant(
            id=uuid.uuid4(),
            name="Demo MoMo ZM",
            market=Market.ZM,
            factor_set=FactorSet.MOBILE_WALLET,
            plan=Plan.STARTER,
            is_active=True,
            alert_threshold=0.20,
            webhook_secret="whsec_" + secrets.token_urlsafe(32),
            created_at=now,
            updated_at=now,
        )
        # A brand-new tenant with no scores/outcomes/alerts/notifications —
        # for verifying the first-time non-technical-lender experience.
        # Everything a lender gets on registration is here (default factor
        # weights, one API key, admin + manager users) but no historical
        # data, so every page's empty state is exercised.
        fresh_tenant = Tenant(
            id=uuid.uuid4(),
            name="Fresh Lender (Demo)",
            market=Market.SA,
            factor_set=FactorSet.CARD_DEBIT,
            plan=Plan.PILOT,
            is_active=True,
            alert_threshold=0.20,
            webhook_secret="whsec_" + secrets.token_urlsafe(32),
            created_at=now,
            updated_at=now,
        )
        # Zambia payroll-deduction lender (Lumo-style — first live prospect).
        # Salary advances collected via payroll deduction; threshold headroom
        # is the dominant risk driver.
        payroll_tenant = Tenant(
            id=uuid.uuid4(),
            name="Demo Payroll ZM",
            market=Market.ZM,
            factor_set=FactorSet.PAYROLL,
            plan=Plan.PILOT,
            is_active=True,
            alert_threshold=0.20,
            webhook_secret="whsec_" + secrets.token_urlsafe(32),
            created_at=now,
            updated_at=now,
        )
        db.add_all([sa_tenant, zm_tenant, fresh_tenant, payroll_tenant])

        # ---- API Keys ----
        # New format: pk_test_<12-hex lookup_id>_<43-char secret>.
        # `lookup_id` is the DB's UNIQUE indexed column the auth path
        # uses; `key_prefix` is the display form for the dashboard.
        sa_raw, sa_hash, sa_lookup, sa_prefix = generate_api_key("pk_test_")
        db.add(ApiKey(
            tenant_id=sa_tenant.id,
            lookup_id=sa_lookup,
            key_hash=sa_hash,
            key_prefix=sa_prefix,
            label="Test Key",
            is_active=True,
        ))
        zm_raw, zm_hash, zm_lookup, zm_prefix = generate_api_key("pk_test_")
        db.add(ApiKey(
            tenant_id=zm_tenant.id,
            lookup_id=zm_lookup,
            key_hash=zm_hash,
            key_prefix=zm_prefix,
            label="Test Key",
            is_active=True,
        ))
        # Fresh tenant gets a key too — a real registered lender would have
        # one from onboarding. Withholding it would make the "API Keys" tab
        # look broken and force the tester to create one before they can even
        # walk through the empty states.
        fresh_raw, fresh_hash, fresh_lookup, fresh_prefix = generate_api_key("pk_test_")
        db.add(ApiKey(
            tenant_id=fresh_tenant.id,
            lookup_id=fresh_lookup,
            key_hash=fresh_hash,
            key_prefix=fresh_prefix,
            label="Default Key",
            is_active=True,
        ))
        payroll_raw, payroll_hash, payroll_lookup, payroll_prefix = generate_api_key("pk_test_")
        db.add(ApiKey(
            tenant_id=payroll_tenant.id,
            lookup_id=payroll_lookup,
            key_hash=payroll_hash,
            key_prefix=payroll_prefix,
            label="Test Key",
            is_active=True,
        ))

        # ---- Factor Weights ----
        # Weights are per collection method. Each tenant gets one row per
        # (method, factor) for every method their business actually uses —
        # mirrors what the migration backfilled and what the weights UI
        # expects to see. CARD_DEBIT tenants get both CARD and DEBIT_ORDER
        # (they'll appear as two sub-tabs in the dashboard); the wallet and
        # payroll tenants get one method each.
        tenant_methods: list[tuple[object, list[CollectionMethod]]] = [
            (sa_tenant, [CollectionMethod.CARD, CollectionMethod.DEBIT_ORDER]),
            (zm_tenant, [CollectionMethod.MOBILE_MONEY]),
            (fresh_tenant, [CollectionMethod.CARD, CollectionMethod.DEBIT_ORDER]),
            (payroll_tenant, [CollectionMethod.PAYROLL]),
        ]
        for tenant, methods in tenant_methods:
            for method in methods:
                for factor_name, weight in get_default_weights_for_method(method).items():
                    db.add(FactorWeight(
                        tenant_id=tenant.id,
                        collection_method=method.value,
                        factor_name=factor_name,
                        weight=weight,
                        updated_at=now,
                    ))

        # ---- Users ----
        admin_hash = hash_password("admin123")

        db.add(User(
            tenant_id=sa_tenant.id,
            email="admin@demo-sa.paypredict.dev",
            name="SA Admin",
            password_hash=admin_hash,
            role=UserRole.ADMIN,
        ))
        db.add(User(
            tenant_id=sa_tenant.id,
            email="viewer@demo-sa.paypredict.dev",
            name="SA Viewer",
            password_hash=hash_password("viewer123"),
            role=UserRole.VIEWER,
        ))
        db.add(User(
            tenant_id=zm_tenant.id,
            email="admin@demo-zm.paypredict.dev",
            name="ZM Admin",
            password_hash=admin_hash,
            role=UserRole.ADMIN,
        ))
        db.add(User(
            tenant_id=zm_tenant.id,
            email="viewer@demo-zm.paypredict.dev",
            name="ZM Viewer",
            password_hash=hash_password("viewer123"),
            role=UserRole.VIEWER,
        ))
        # Fresh tenant users: one admin, one manager. Skipping viewer here on
        # purpose — a brand-new lender wouldn't usually have viewers seat 1.
        db.add(User(
            tenant_id=fresh_tenant.id,
            email="admin@demo-fresh.paypredict.dev",
            name="Fresh Admin",
            password_hash=admin_hash,
            role=UserRole.ADMIN,
        ))
        db.add(User(
            tenant_id=fresh_tenant.id,
            email="manager@demo-fresh.paypredict.dev",
            name="Fresh Manager",
            password_hash=hash_password("manager123"),
            role=UserRole.MANAGER,
        ))
        db.add(User(
            tenant_id=payroll_tenant.id,
            email="admin@demo-payroll.paypredict.dev",
            name="Payroll Admin",
            password_hash=admin_hash,
            role=UserRole.ADMIN,
        ))
        db.add(User(
            tenant_id=payroll_tenant.id,
            email="viewer@demo-payroll.paypredict.dev",
            name="Payroll Viewer",
            password_hash=hash_password("viewer123"),
            role=UserRole.VIEWER,
        ))

        # ---- Scored Collections ----
        sa_methods = [CollectionMethod.CARD, CollectionMethod.CARD, CollectionMethod.DEBIT_ORDER]
        risk_biases = ["high", "medium", "medium", "low", "low", "low"]

        all_scores: list[tuple[ScoreResult, ScoreRequest]] = []

        # Generic journey shapes — (pattern, loan_size, weight). Repeated
        # weight controls how often each shape shows up in a demo tenant.
        JOURNEY_SHAPES = [
            ("all_success", 6, 30),
            ("in_progress", 6, 25),
            ("late_default", 6, 15),
            ("mid_default", 4, 15),
            ("early_default", 4, 10),
            ("all_success", 12, 5),
        ]

        def _pick_journey_shape(rng: random.Random) -> tuple[str, int]:
            pattern, size, _ = rng.choices(
                JOURNEY_SHAPES, weights=[w for _, _, w in JOURNEY_SHAPES], k=1
            )[0]
            return pattern, size

        # ---- SA named personas (card + debit order) ----
        # Same treatment as Rosemary's payroll trio: three scripted
        # customers whose journeys mirror the archetype scenarios a
        # BNPL / EFT lender will recognise on first look.

        # CUST_THABO_001 — repeat BNPL customer, always paid on time.
        # The best-customer archetype for a card lender: 6 clean
        # instalments, scores stay LOW as the track record builds.
        await _seed_journey_customer(
            db=db,
            engine=engine,
            tenant=sa_tenant,
            method=CollectionMethod.CARD,
            factor_set="CARD_DEBIT",
            currency=CollectionCurrency.ZAR,
            customer_id="CUST_THABO_001",
            loan_size=6,
            pattern="all_success",
            base_amount=1500.0,
            customer_template_fn=_sa_customer,
            template_kwargs={"risk_bias": "low"},
            rng=rng,
            now=now,
        )

        # CUST_LERATO_002 — card expiring mid-loan. First 3 instalments
        # clean; instalment 4 pending with the card ~10 days from
        # expiry, so `card_health` fires HIGH → recommended_action
        # flips to flag_for_review. The "we would have caught it"
        # equivalent for card lenders.
        near_expiry_date = (now + timedelta(days=10)).date().isoformat()
        await _seed_journey_customer(
            db=db,
            engine=engine,
            tenant=sa_tenant,
            method=CollectionMethod.CARD,
            factor_set="CARD_DEBIT",
            currency=CollectionCurrency.ZAR,
            customer_id="CUST_LERATO_002",
            loan_size=4,
            pattern="in_progress",  # first 2 succeed, later ones pending
            base_amount=850.0,
            customer_template_fn=_sa_customer,
            template_kwargs={"risk_bias": "low"},
            rng=rng,
            now=now,
            per_instalment_override={
                # Instalment 4: card expires in 10 days.
                4: {"card_expiry_date": near_expiry_date},
            },
        )

        # CUST_ANDILE_003 — debit-order customer, early default. Shows
        # the `debit_order_return_history` factor fired against a real
        # journey (previous instalment failed with insufficient_funds).
        await _seed_journey_customer(
            db=db,
            engine=engine,
            tenant=sa_tenant,
            method=CollectionMethod.DEBIT_ORDER,
            factor_set="CARD_DEBIT",
            currency=CollectionCurrency.ZAR,
            customer_id="CUST_ANDILE_003",
            loan_size=4,
            pattern="early_default",  # 1st fails, rest mixed
            base_amount=2400.0,
            customer_template_fn=_sa_customer,
            template_kwargs={"risk_bias": "high"},
            rng=rng,
            now=now,
        )

        # ---- SA journey customers (20 × ~6 instalments ≈ 120 rows) ----
        for j in range(20):
            pattern, loan_size = _pick_journey_shape(rng)
            method = rng.choice(sa_methods)
            # Bias picked once per loan so the customer has a consistent
            # profile across their journey.
            bias = "low" if pattern == "all_success" else rng.choice(["medium", "low"])
            await _seed_journey_customer(
                db=db,
                engine=engine,
                tenant=sa_tenant,
                method=method,
                factor_set="CARD_DEBIT",
                currency=CollectionCurrency.ZAR,
                customer_id=f"cust_sa_j_{j + 1:03d}",
                loan_size=loan_size,
                pattern=pattern,
                base_amount=round(rng.uniform(500, 4000), 2),
                customer_template_fn=_sa_customer,
                template_kwargs={"risk_bias": bias},
                rng=rng,
                now=now,
            )

        # SA singletons: 30 (was 150 pre-journey)
        for i in range(30):
            bias = rng.choice(risk_biases)
            method = rng.choice(sa_methods)
            customer_data = _sa_customer(rng, bias)
            amount = round(rng.uniform(300, 8000), 2)
            due_days = rng.randint(-2, 30)
            due_date = (now + timedelta(days=due_days)).date()

            collection_data = {
                "collection_amount": amount,
                "collection_due_date": due_date,
                "collection_method": method.value,
                "collection_currency": "ZAR",
            }

            scoring_result = engine.score(
                factor_set="CARD_DEBIT",
                customer_data=customer_data,
                collection_data=collection_data,
                collection_method=method,
            )

            timing = optimise_collection_date(
                engine,
                customer_data=customer_data,
                collection_data=collection_data,
                collection_method=method,
                original_score=scoring_result.score,
                today=due_date,  # seed dates can be in the past — anchor floor to the due date itself
            )
            sa_recommended_action = (
                "shift_date" if timing.should_shift else scoring_result.recommended_action
            )

            scored_at = now - timedelta(hours=rng.randint(1, 720))

            # Build JSON-safe payload (dates → str, enums → str)
            payload = {
                "customer_data": customer_data,
                "collection_amount": amount,
                "collection_due_date": due_date.isoformat(),
                "collection_method": method.value,
                "collection_currency": "ZAR",
            }

            req = ScoreRequest(
                id=uuid.uuid4(),
                tenant_id=sa_tenant.id,
                external_customer_id=f"cust_sa_{i + 1:03d}",
                external_collection_id=f"col_sa_{i + 1:03d}",
                collection_amount=Decimal(str(amount)),
                collection_currency=CollectionCurrency.ZAR,
                collection_due_date=due_date,
                collection_method=method,
                request_payload=payload,
                created_at=scored_at,
            )

            res = ScoreResult(
                id=uuid.uuid4(),
                score_request_id=req.id,
                tenant_id=sa_tenant.id,
                score=scoring_result.score,
                risk_level=RiskLevel(scoring_result.risk_level),
                factors={
                    "evaluated": [
                        {
                            "factor_name": f.factor_name,
                            "raw_score": f.raw_score,
                            "weight": f.weight,
                            "weighted_score": f.weighted_score,
                            "explanation": f.explanation,
                        }
                        for f in scoring_result.factors
                    ],
                    "skipped": scoring_result.skipped_factors,
                },
                recommended_action=sa_recommended_action,
                recommended_collection_date=timing.recommended_date,
                recommended_score=timing.recommended_score,
                score_improvement=(
                    timing.score_improvement if timing.should_shift else None
                ),
                model_version=scoring_result.model_version,
                scoring_duration_ms=scoring_result.scoring_duration_ms,
                weights_snapshot=scoring_result.weights_snapshot,
                created_at=scored_at,
            )
            db.add(req)
            db.add(res)
            all_scores.append((res, req))

        # ---- ZM MoMo named personas ----
        # Same shape as SA / Payroll named trios: three archetype
        # customers a mobile-money lender will recognise instantly.

        # CUST_MWAKA_001 — reliable Friday-salary wallet user. Regular
        # inflows, healthy balance, 6 clean instalments. Best-customer
        # archetype for MoMo lenders.
        await _seed_journey_customer(
            db=db,
            engine=engine,
            tenant=zm_tenant,
            method=CollectionMethod.MOBILE_MONEY,
            factor_set="MOBILE_WALLET",
            currency=CollectionCurrency.ZMW,
            customer_id="CUST_MWAKA_001",
            loan_size=6,
            pattern="all_success",
            base_amount=400.0,
            customer_template_fn=_zm_customer,
            template_kwargs={"risk_bias": "low"},
            rng=rng,
            now=now,
        )

        # CUST_CHOMBA_002 — wallet balance deteriorating over time.
        # 6 instalments; on instalments 5+6 wallet_balance_current
        # drops well below the 7-day average, so wallet_balance_trend
        # fires. First 4 succeed, then default.
        await _seed_journey_customer(
            db=db,
            engine=engine,
            tenant=zm_tenant,
            method=CollectionMethod.MOBILE_MONEY,
            factor_set="MOBILE_WALLET",
            currency=CollectionCurrency.ZMW,
            customer_id="CUST_CHOMBA_002",
            loan_size=6,
            pattern="late_default",
            base_amount=650.0,
            customer_template_fn=_zm_customer,
            template_kwargs={"risk_bias": "medium"},
            rng=rng,
            now=now,
            per_instalment_override={
                # Balance collapsed by instalment 6 — wallet_balance_trend
                # should read this as a deteriorating customer.
                5: {"wallet_balance_current": 80.0, "wallet_balance_7d_avg": 400.0},
                6: {"wallet_balance_current": 40.0, "wallet_balance_7d_avg": 300.0},
            },
        )

        # CUST_KABWE_003 — loan stacking. High active_loan_count +
        # loans_taken_last_90d, so loan_cycling_behaviour and
        # concurrent_loan_count both fire. 4 instalments, mid_default.
        await _seed_journey_customer(
            db=db,
            engine=engine,
            tenant=zm_tenant,
            method=CollectionMethod.MOBILE_MONEY,
            factor_set="MOBILE_WALLET",
            currency=CollectionCurrency.ZMW,
            customer_id="CUST_KABWE_003",
            loan_size=4,
            pattern="mid_default",
            base_amount=350.0,
            customer_template_fn=_zm_customer,
            template_kwargs={"risk_bias": "high"},
            rng=rng,
            now=now,
            per_instalment_override={
                # Force cycling signals — high active loans + recent
                # new borrowing throughout the loan.
                1: {"active_loan_count": 4, "loans_taken_last_90d": 3},
                2: {"active_loan_count": 4, "loans_taken_last_90d": 3},
                3: {"active_loan_count": 5, "loans_taken_last_90d": 4},
                4: {"active_loan_count": 5, "loans_taken_last_90d": 4},
            },
        )

        # ---- ZM MoMo journey customers (10 × ~5 instalments ≈ 50 rows) ----
        for j in range(10):
            pattern, loan_size = _pick_journey_shape(rng)
            bias = "low" if pattern == "all_success" else rng.choice(["medium", "low"])
            await _seed_journey_customer(
                db=db,
                engine=engine,
                tenant=zm_tenant,
                method=CollectionMethod.MOBILE_MONEY,
                factor_set="MOBILE_WALLET",
                currency=CollectionCurrency.ZMW,
                customer_id=f"cust_zm_j_{j + 1:03d}",
                loan_size=loan_size,
                pattern=pattern,
                base_amount=round(rng.uniform(100, 1200), 2),
                customer_template_fn=_zm_customer,
                template_kwargs={"risk_bias": bias},
                rng=rng,
                now=now,
            )

        # ZM singletons: 30 (was 80 pre-journey)
        for i in range(30):
            bias = rng.choice(risk_biases)
            customer_data = _zm_customer(rng, bias)
            amount = round(rng.uniform(50, 1500), 2)
            due_days = rng.randint(-1, 30)
            due_date = (now + timedelta(days=due_days)).date()

            collection_data = {
                "collection_amount": amount,
                "collection_due_date": due_date,
                "collection_method": "MOBILE_MONEY",
                "collection_currency": "ZMW",
            }

            scoring_result = engine.score(
                factor_set="MOBILE_WALLET",
                customer_data=customer_data,
                collection_data=collection_data,
                collection_method=CollectionMethod.MOBILE_MONEY,
            )

            timing = optimise_collection_date(
                engine,
                customer_data=customer_data,
                collection_data=collection_data,
                collection_method=CollectionMethod.MOBILE_MONEY,
                original_score=scoring_result.score,
                today=due_date,
            )
            zm_recommended_action = (
                "shift_date" if timing.should_shift else scoring_result.recommended_action
            )

            scored_at = now - timedelta(hours=rng.randint(1, 720))

            payload = {
                "customer_data": customer_data,
                "collection_amount": amount,
                "collection_due_date": due_date.isoformat(),
                "collection_method": "MOBILE_MONEY",
                "collection_currency": "ZMW",
            }

            req = ScoreRequest(
                id=uuid.uuid4(),
                tenant_id=zm_tenant.id,
                external_customer_id=f"cust_zm_{i + 1:03d}",
                external_collection_id=f"col_zm_{i + 1:03d}",
                collection_amount=Decimal(str(amount)),
                collection_currency=CollectionCurrency.ZMW,
                collection_due_date=due_date,
                collection_method=CollectionMethod.MOBILE_MONEY,
                request_payload=payload,
                created_at=scored_at,
            )

            res = ScoreResult(
                id=uuid.uuid4(),
                score_request_id=req.id,
                tenant_id=zm_tenant.id,
                score=scoring_result.score,
                risk_level=RiskLevel(scoring_result.risk_level),
                factors={
                    "evaluated": [
                        {
                            "factor_name": f.factor_name,
                            "raw_score": f.raw_score,
                            "weight": f.weight,
                            "weighted_score": f.weighted_score,
                            "explanation": f.explanation,
                        }
                        for f in scoring_result.factors
                    ],
                    "skipped": scoring_result.skipped_factors,
                },
                recommended_action=zm_recommended_action,
                recommended_collection_date=timing.recommended_date,
                recommended_score=timing.recommended_score,
                score_improvement=(
                    timing.score_improvement if timing.should_shift else None
                ),
                model_version=scoring_result.model_version,
                scoring_duration_ms=scoring_result.scoring_duration_ms,
                weights_snapshot=scoring_result.weights_snapshot,
                created_at=scored_at,
            )
            db.add(req)
            db.add(res)
            all_scores.append((res, req))

        # ---- Payroll (Zambia) named personas (Rosemary / Lumo call) ----
        # Three scripted customers whose journeys mirror real scenarios
        # Rosemary at Lumo described. The demo user (or Rosemary
        # herself) recognises the shape immediately and the product
        # "sells itself" (her words).

        # EMP_ROSE_001 — government worker whose latest deduction would
        # breach the 40% cap. Two prior successful instalments; the
        # third (still pending) has current_total_deductions engineered
        # near the ceiling so threshold_headroom fires HIGH.
        rose_gross = 9500.0
        rose_headroom_deductions = round(rose_gross * 0.40 * 0.96, 2)  # 96% of cap
        await _seed_journey_customer(
            db=db,
            engine=engine,
            tenant=payroll_tenant,
            method=CollectionMethod.PAYROLL,
            factor_set="PAYROLL",
            currency=CollectionCurrency.ZMW,
            customer_id="EMP_ROSE_001",
            loan_size=3,
            pattern="in_progress",  # first 2 succeed, 3rd pending
            base_amount=1200.0,
            customer_template_fn=_payroll_customer,
            template_kwargs={"risk_bias": "low", "segment": "government"},
            rng=rng,
            now=now,
            per_instalment_override={
                # Instalment 3: engineer the "over the 40% cap" scenario.
                3: {
                    "gross_salary": rose_gross,
                    "current_total_deductions": rose_headroom_deductions,
                    "net_pay": round(rose_gross - rose_headroom_deductions - (rose_gross * 0.15), 2),
                    "active_loan_count": 3,
                },
            },
        )

        # EMP_JOHN_002 — repeat borrower who's always paid on time.
        # Lumo's best-customer archetype. 12-instalment loan, all clean.
        await _seed_journey_customer(
            db=db,
            engine=engine,
            tenant=payroll_tenant,
            method=CollectionMethod.PAYROLL,
            factor_set="PAYROLL",
            currency=CollectionCurrency.ZMW,
            customer_id="EMP_JOHN_002",
            loan_size=12,
            pattern="all_success",
            base_amount=800.0,
            customer_template_fn=_payroll_customer,
            template_kwargs={"risk_bias": "low", "segment": "government"},
            rng=rng,
            now=now,
        )

        # EMP_MOSES_003 — miner who paid twice then went silent.
        # Segment volatility + mid-loan default = the classic "we should
        # have seen it coming" case the pitch calls out.
        await _seed_journey_customer(
            db=db,
            engine=engine,
            tenant=payroll_tenant,
            method=CollectionMethod.PAYROLL,
            factor_set="PAYROLL",
            currency=CollectionCurrency.ZMW,
            customer_id="EMP_MOSES_003",
            loan_size=6,
            pattern="mid_default",
            base_amount=1500.0,
            customer_template_fn=_payroll_customer,
            template_kwargs={"risk_bias": "medium", "segment": "mining"},
            rng=rng,
            now=now,
        )

        # ---- Payroll generic journeys (5 × ~4 = ~20 rows) ----
        for j in range(5):
            pattern, loan_size = _pick_journey_shape(rng)
            # Payroll loans are short (2-6 months typically) so cap size
            loan_size = min(loan_size, 6)
            segment = rng.choice(["government", "government", "government", "mining"])
            bias = "low" if pattern == "all_success" else rng.choice(["medium", "low"])
            await _seed_journey_customer(
                db=db,
                engine=engine,
                tenant=payroll_tenant,
                method=CollectionMethod.PAYROLL,
                factor_set="PAYROLL",
                currency=CollectionCurrency.ZMW,
                customer_id=f"emp_{segment[:3]}_j_{j + 1:03d}",
                loan_size=loan_size,
                pattern=pattern,
                base_amount=round(rng.uniform(500, 3000), 2),
                customer_template_fn=_payroll_customer,
                template_kwargs={"risk_bias": bias, "segment": segment},
                rng=rng,
                now=now,
            )

        # Payroll singletons: 9 (was 50 pre-journey; ~80% gov / 20% miners)
        payroll_risk_biases = ["high", "medium", "medium", "low", "low", "low", "low", "low", "low"]
        rng.shuffle(payroll_risk_biases)
        for i in range(9):
            segment = "government" if i < 7 else "mining"
            bias = payroll_risk_biases[i]
            customer_data = _payroll_customer(rng, bias, segment)
            amount = round(rng.uniform(500, 4500), 2)  # ZMW salary-advance range
            due_days = rng.randint(-2, 30)
            due_date = (now + timedelta(days=due_days)).date()

            collection_data = {
                "collection_amount": amount,
                "collection_due_date": due_date,
                "collection_method": "PAYROLL",
                "collection_currency": "ZMW",
            }

            scoring_result = engine.score(
                factor_set="PAYROLL",
                customer_data=customer_data,
                collection_data=collection_data,
                collection_method=CollectionMethod.PAYROLL,
            )
            timing = optimise_collection_date(
                engine,
                customer_data=customer_data,
                collection_data=collection_data,
                collection_method=CollectionMethod.PAYROLL,
                original_score=scoring_result.score,
                today=due_date,
            )
            payroll_recommended_action = (
                "shift_date" if timing.should_shift else scoring_result.recommended_action
            )

            scored_at = now - timedelta(hours=rng.randint(1, 720))
            payload = {
                "customer_data": customer_data,
                "collection_amount": amount,
                "collection_due_date": due_date.isoformat(),
                "collection_method": "PAYROLL",
                "collection_currency": "ZMW",
            }

            req = ScoreRequest(
                id=uuid.uuid4(),
                tenant_id=payroll_tenant.id,
                external_customer_id=f"emp_{segment[:3]}_{i + 1:03d}",
                external_collection_id=f"ded_{now.year}_{now.month:02d}_{i + 1:03d}",
                collection_amount=Decimal(str(amount)),
                collection_currency=CollectionCurrency.ZMW,
                collection_due_date=due_date,
                collection_method=CollectionMethod.PAYROLL,
                request_payload=payload,
                created_at=scored_at,
            )
            res = ScoreResult(
                id=uuid.uuid4(),
                score_request_id=req.id,
                tenant_id=payroll_tenant.id,
                score=scoring_result.score,
                risk_level=RiskLevel(scoring_result.risk_level),
                factors={
                    "evaluated": [
                        {
                            "factor_name": f.factor_name,
                            "raw_score": f.raw_score,
                            "weight": f.weight,
                            "weighted_score": f.weighted_score,
                            "explanation": f.explanation,
                        }
                        for f in scoring_result.factors
                    ],
                    "skipped": scoring_result.skipped_factors,
                },
                recommended_action=payroll_recommended_action,
                recommended_collection_date=timing.recommended_date,
                recommended_score=timing.recommended_score,
                score_improvement=(
                    timing.score_improvement if timing.should_shift else None
                ),
                model_version=scoring_result.model_version,
                scoring_duration_ms=scoring_result.scoring_duration_ms,
                weights_snapshot=scoring_result.weights_snapshot,
                created_at=scored_at,
            )
            db.add(req)
            db.add(res)
            all_scores.append((res, req))

        # ---- Outcomes (~80% of scores) ----
        outcome_count = 0
        for res, req in all_scores:
            if rng.random() > 0.80:
                continue  # ~20% have no outcome yet

            risk = res.risk_level.value
            # Outcomes correlate with risk: HIGH scores fail more often
            if risk == "HIGH":
                is_success = rng.random() < 0.25
            elif risk == "MEDIUM":
                is_success = rng.random() < 0.60
            else:
                is_success = rng.random() < 0.92

            if is_success:
                outcome_status = OutcomeStatus.SUCCESS
                failure_reason = None
                failure_category = None
            else:
                outcome_status = OutcomeStatus.FAILED
                reason, category = rng.choice(FAILURE_REASONS)
                failure_reason = reason
                failure_category = category

            attempted_at = req.collection_due_date
            attempted_dt = datetime(
                attempted_at.year, attempted_at.month, attempted_at.day,
                8, 0, 0, tzinfo=timezone.utc,
            )

            db.add(Outcome(
                id=uuid.uuid4(),
                score_result_id=res.id,
                tenant_id=req.tenant_id,
                external_collection_id=req.external_collection_id,
                outcome=outcome_status,
                failure_reason=failure_reason,
                failure_category=failure_category,
                amount_collected=req.collection_amount if is_success else None,
                attempted_at=attempted_dt,
                reported_at=attempted_dt + timedelta(hours=rng.randint(1, 24)),
            ))
            outcome_count += 1

        # Flush scores + outcomes before adding alerts/backtests that reference tenants
        await db.flush()

        # ---- Alerts (3 for SA tenant: 1 unread, 2 read) ----
        db.add(Alert(
            id=uuid.uuid4(),
            tenant_id=sa_tenant.id,
            alert_type=AlertType.HIGH_RISK_BATCH,
            message="12 of 50 collections (24%) scored as high risk — exceeds 20% threshold",
            metadata_={"high_risk_count": 12, "total": 50, "percentage": 0.24, "threshold": 0.2},
            is_read=False,
            created_at=now - timedelta(hours=2),
        ))
        db.add(Alert(
            id=uuid.uuid4(),
            tenant_id=sa_tenant.id,
            alert_type=AlertType.HIGH_RISK_BATCH,
            message="8 of 30 collections (27%) scored as high risk — exceeds 20% threshold",
            metadata_={"high_risk_count": 8, "total": 30, "percentage": 0.27, "threshold": 0.2},
            is_read=True,
            created_at=now - timedelta(days=3),
        ))
        db.add(Alert(
            id=uuid.uuid4(),
            tenant_id=sa_tenant.id,
            alert_type=AlertType.COLLECTION_RATE_DROP,
            message="Collection rate dropped to 71% (below 75% baseline)",
            metadata_={"current_rate": 0.71, "baseline": 0.75},
            is_read=True,
            created_at=now - timedelta(days=7),
        ))

        # ---- Backtest run (1 completed, 50 items for SA tenant) ----
        bt_items_data = []
        for i in range(50):
            bias = rng.choice(risk_biases)
            cust = _sa_customer(rng, bias)
            amt = round(rng.uniform(500, 5000), 2)
            method = rng.choice(sa_methods)
            outcome_val = "FAILED" if rng.random() < 0.3 else "SUCCESS"

            coll_data = {
                "collection_amount": amt,
                "collection_due_date": (now - timedelta(days=rng.randint(30, 180))).date(),
                "collection_method": method.value,
                "collection_currency": "ZAR",
            }
            sr = engine.score(
                factor_set="CARD_DEBIT",
                customer_data=cust,
                collection_data=coll_data,
                collection_method=method,
            )
            matched = (
                (sr.risk_level == "HIGH" and outcome_val == "FAILED")
                or (sr.risk_level == "LOW" and outcome_val == "SUCCESS")
                or sr.risk_level == "MEDIUM"
            )
            bt_items_data.append({
                "cust_id": f"bt_cust_{i+1:03d}",
                "col_id": f"bt_col_{i+1:03d}",
                "amount": Decimal(str(amt)),
                "method": method.value,
                "score": sr.score,
                "risk": sr.risk_level,
                "outcome": outcome_val,
                "reason": rng.choice(["insufficient_funds", "do_not_honour", None]) if outcome_val == "FAILED" else None,
                "factors": {
                    "evaluated": [{"factor_name": f.factor_name, "raw_score": f.raw_score, "weight": f.weight, "weighted_score": f.weighted_score, "explanation": f.explanation} for f in sr.factors],
                    "skipped": sr.skipped_factors,
                },
                "matched": matched,
            })

        bt_matched = sum(1 for d in bt_items_data if d["matched"])
        bt_failed = [d for d in bt_items_data if d["outcome"] == "FAILED"]
        bt_accuracy = bt_matched / len(bt_items_data) if bt_items_data else 0
        bt_failed_value = sum(float(d["amount"]) for d in bt_failed)
        bt_flagged_failures = [d for d in bt_failed if d["risk"] in ("HIGH", "MEDIUM")]
        bt_flagged = sum(float(d["amount"]) for d in bt_flagged_failures)

        bt_run = BacktestRun(
            id=uuid.uuid4(),
            tenant_id=sa_tenant.id,
            name="Q4 2025 Card Collections",
            status=BacktestStatus.COMPLETED,
            total_collections=50,
            factor_set_used="CARD_DEBIT",
            # New per-method shape: `weights_used[method] = {factor: weight}`
            # so replays can tell which method each row was measured against.
            weights_used={
                CollectionMethod.CARD.value: get_default_weights_for_method(CollectionMethod.CARD),
                CollectionMethod.DEBIT_ORDER.value: get_default_weights_for_method(CollectionMethod.DEBIT_ORDER),
            },
            summary={
                "overall_accuracy": round(bt_accuracy, 3),
                "collection_rate_actual": round(1 - len(bt_failed) / 50, 3),
                "collection_rate_if_acted": round(min(1, 1 - len(bt_failed) / 50 + len(bt_flagged_failures) * 0.6 / 50), 3),
                "estimated_annual_recovery": round(bt_flagged * 0.6 * 12, 2),
                "total_failed_value": round(bt_failed_value, 2),
                "flagged_in_advance_value": round(bt_flagged, 2),
            },
            confusion_matrix={
                "predicted_high_actual_failed": sum(1 for d in bt_items_data if d["risk"] == "HIGH" and d["outcome"] == "FAILED"),
                "predicted_high_actual_success": sum(1 for d in bt_items_data if d["risk"] == "HIGH" and d["outcome"] == "SUCCESS"),
                "predicted_medium_actual_failed": sum(1 for d in bt_items_data if d["risk"] == "MEDIUM" and d["outcome"] == "FAILED"),
                "predicted_medium_actual_success": sum(1 for d in bt_items_data if d["risk"] == "MEDIUM" and d["outcome"] == "SUCCESS"),
                "predicted_low_actual_failed": sum(1 for d in bt_items_data if d["risk"] == "LOW" and d["outcome"] == "FAILED"),
                "predicted_low_actual_success": sum(1 for d in bt_items_data if d["risk"] == "LOW" and d["outcome"] == "SUCCESS"),
            },
            top_failure_factors=[],
            started_at=now - timedelta(days=5),
            completed_at=now - timedelta(days=5) + timedelta(seconds=12),
            created_at=now - timedelta(days=5),
        )
        db.add(bt_run)

        for d in bt_items_data:
            db.add(BacktestItem(
                id=uuid.uuid4(),
                backtest_run_id=bt_run.id,
                external_customer_id=d["cust_id"],
                external_collection_id=d["col_id"],
                collection_amount=d["amount"],
                collection_method=d["method"],
                predicted_score=d["score"],
                predicted_risk_level=d["risk"],
                actual_outcome=d["outcome"],
                failure_reason=d["reason"],
                factors=d["factors"],
                prediction_matched=d["matched"],
            ))

        # ---- Notifications (5 for SA tenant: 3 unread, 2 read) ----
        sa_admin_id = None
        # Find the SA admin user we created earlier
        from sqlalchemy import select as sa_select
        admin_result = await db.execute(
            sa_select(User).where(User.email == "admin@demo-sa.paypredict.dev")
        )
        sa_admin = admin_result.scalar_one_or_none()
        if sa_admin:
            sa_admin_id = sa_admin.id

        db.add(Notification(
            id=uuid.uuid4(),
            tenant_id=sa_tenant.id,
            category=NotificationCategory.SYSTEM,
            severity=NotificationSeverity.CRITICAL,
            event_type="high_risk_batch",
            title="High-risk batch detected",
            message="12 of 50 collections (24%) scored as high risk — exceeds your 20% threshold",
            link_to="/dashboard?risk_level=HIGH",
            link_label="View high-risk collections",
            metadata_={"high_risk_count": 12, "total_count": 50, "percentage": 0.24, "threshold": 0.2},
            is_read=False,
            created_at=now - timedelta(hours=2),
        ))
        db.add(Notification(
            id=uuid.uuid4(),
            tenant_id=sa_tenant.id,
            category=NotificationCategory.SYSTEM,
            severity=NotificationSeverity.WARNING,
            event_type="collection_rate_drop",
            title="Collection rate dropping",
            message="Collection rate dropped to 72.1% — down 6.3% from last week",
            link_to="/dashboard/analytics",
            link_label="View analytics",
            metadata_={"current_rate": 0.721, "drop": 0.063},
            is_read=False,
            created_at=now - timedelta(hours=5),
        ))
        db.add(Notification(
            id=uuid.uuid4(),
            tenant_id=sa_tenant.id,
            category=NotificationCategory.SYSTEM,
            severity=NotificationSeverity.INFO,
            event_type="backtest_complete",
            title="Backtest complete",
            message="Backtest completed — 50 collections scored with 82% accuracy",
            link_to="/dashboard/backtest",
            link_label="View backtest results",
            metadata_={"total_collections": 50, "accuracy": 0.82},
            is_read=False,
            created_at=now - timedelta(days=1),
        ))
        db.add(Notification(
            id=uuid.uuid4(),
            tenant_id=sa_tenant.id,
            category=NotificationCategory.ACTIVITY,
            severity=NotificationSeverity.INFO,
            event_type="weights_updated",
            title="Factor weights updated",
            message="Factor weights updated by SA Admin",
            link_to="/dashboard/settings?tab=weights",
            link_label="View weights",
            metadata_={"actor_name": "SA Admin"},
            actor_id=sa_admin_id,
            is_read=True,
            read_at=now - timedelta(days=2, hours=-1),
            created_at=now - timedelta(days=2),
        ))
        db.add(Notification(
            id=uuid.uuid4(),
            tenant_id=sa_tenant.id,
            category=NotificationCategory.ACTIVITY,
            severity=NotificationSeverity.INFO,
            event_type="api_key_created",
            title="API key created",
            message="New API key 'Production' created by SA Admin",
            link_to="/dashboard/settings?tab=api-keys",
            link_label="View API keys",
            metadata_={"actor_name": "SA Admin", "key_label": "Production"},
            actor_id=sa_admin_id,
            is_read=True,
            read_at=now - timedelta(days=3, hours=-2),
            created_at=now - timedelta(days=3),
        ))

        await db.commit()

        # ---- Summary ----
        high = sum(1 for r, _ in all_scores if r.risk_level == RiskLevel.HIGH)
        medium = sum(1 for r, _ in all_scores if r.risk_level == RiskLevel.MEDIUM)
        low = sum(1 for r, _ in all_scores if r.risk_level == RiskLevel.LOW)

        print("Seed completed successfully!")
        print()
        print(f"  Scores:   {len(all_scores)} (HIGH={high}, MEDIUM={medium}, LOW={low})")
        print(f"  Outcomes: {outcome_count} ({outcome_count}/{len(all_scores)} = {outcome_count*100//len(all_scores)}%)")
        print()
        print(f"  Alerts:   3 (1 unread, 2 read)")
        print(f"  Notifs:   5 (3 unread, 2 read)")
        print(f"  Backtest: 1 completed run (50 items)")
        print()
        print("=== SA Tenant (BNPL, CARD + DEBIT_ORDER) ===")
        print(f"  Tenant ID: {sa_tenant.id}")
        print(f"  API Key:   {sa_raw}")
        print(f"  Scores:    ~150 total. Named personas for demo:")
        print(f"             CUST_THABO_001  — repeat card customer, 6 instalments, all clean")
        print(f"             CUST_LERATO_002 — card expires mid-loan (card_health fires HIGH)")
        print(f"             CUST_ANDILE_003 — debit-order early default, 4 instalments")
        print()
        print("=== ZM Tenant (MOBILE_MONEY) ===")
        print(f"  Tenant ID: {zm_tenant.id}")
        print(f"  API Key:   {zm_raw}")
        print(f"  Scores:    ~89 total. Named personas for demo:")
        print(f"             CUST_MWAKA_001  — reliable Friday-salary wallet user, 6 clean")
        print(f"             CUST_CHOMBA_002 — wallet balance deteriorates, late default")
        print(f"             CUST_KABWE_003  — loan stacking, 4 instalments, mid default")
        print()
        print("=== Fresh Lender (Demo) ===")
        print(f"  Tenant ID: {fresh_tenant.id}")
        print(f"  API Key:   {fresh_raw}")
        print(f"  Scores:    0 — empty tenant, exercises every first-time empty state")
        print()
        print("=== Demo Payroll ZM (Lumo-style, PAYROLL) ===")
        print(f"  Tenant ID: {payroll_tenant.id}")
        print(f"  API Key:   {payroll_raw}")
        print(f"  Scores:    ~58 total. Named personas from Rosemary's call:")
        print(f"             EMP_ROSE_001  — gov worker, 3 instalments, 3rd breaches 40% cap")
        print(f"             EMP_JOHN_002  — repeat borrower, 12 instalments, all clean")
        print(f"             EMP_MOSES_003 — miner, 6 instalments, paid twice then default")
        print()
        print("=== Dashboard Login ===")
        print(f"  Admin:   admin@demo-sa.paypredict.dev     / admin123")
        print(f"  Viewer:  viewer@demo-sa.paypredict.dev    / viewer123")
        print(f"  Admin:   admin@demo-zm.paypredict.dev     / admin123")
        print(f"  Viewer:  viewer@demo-zm.paypredict.dev    / viewer123")
        print(f"  Admin:   admin@demo-fresh.paypredict.dev  / admin123    ← fresh, no data")
        print(f"  Manager: manager@demo-fresh.paypredict.dev / manager123 ← fresh, no data")
        print(f"  Admin:   admin@demo-payroll.paypredict.dev / admin123   ← payroll")
        print(f"  Viewer:  viewer@demo-payroll.paypredict.dev / viewer123 ← payroll")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed local demo data.")
    parser.add_argument(
        "--reseed",
        action="store_true",
        help="Wipe existing seed data and re-seed. Use this when dates have gone stale.",
    )
    args = parser.parse_args()
    asyncio.run(seed(reseed=args.reseed))
