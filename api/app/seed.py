"""Seed script for local development and demos.

Creates:
- 2 tenants (SA + ZM) with API keys and default factor weights
- 2 admin users + 2 viewer users (for team management demo)
- 60 scored collections (40 SA + 20 ZM) with real factor breakdowns
- Outcomes for ~80% of scores (mix of SUCCESS/FAILED)
- Prints login credentials and API keys when done

Usage: python -m app.seed
"""

import asyncio
import random
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import bcrypt
from sqlalchemy import select

from app.database import async_session
from app.models.api_key import ApiKey
from app.models.factor_weight import FactorWeight
from app.models.outcome import FailureCategory, Outcome, OutcomeStatus
from app.models.score_request import CollectionCurrency, CollectionMethod, ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.models.tenant import FactorSet, Market, Plan, Tenant
from app.models.user import User, UserRole
from app.scoring.engine import ScoringEngine
from app.scoring.registry import get_default_weights
from app.services.auth_service import hash_password


def generate_api_key(prefix: str) -> tuple[str, str]:
    """Generate an API key and return (raw_key, hashed_key)."""
    raw = prefix + secrets.token_urlsafe(32)
    hashed = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return raw, hashed


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


async def seed() -> None:
    engine = ScoringEngine()
    rng = random.Random(42)  # Deterministic for reproducible demos

    async with async_session() as db:
        # Check if already seeded
        result = await db.execute(select(Tenant).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
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
            created_at=now,
            updated_at=now,
        )
        db.add_all([sa_tenant, zm_tenant])

        # ---- API Keys ----
        sa_raw, sa_hash = generate_api_key("pk_test_")
        db.add(ApiKey(
            tenant_id=sa_tenant.id,
            key_hash=sa_hash,
            key_prefix=sa_raw[:8],
            label="Test Key",
            is_active=True,
        ))
        zm_raw, zm_hash = generate_api_key("pk_test_")
        db.add(ApiKey(
            tenant_id=zm_tenant.id,
            key_hash=zm_hash,
            key_prefix=zm_raw[:8],
            label="Test Key",
            is_active=True,
        ))

        # ---- Factor Weights ----
        for tenant, factor_set in [
            (sa_tenant, "CARD_DEBIT"),
            (zm_tenant, "MOBILE_WALLET"),
        ]:
            for factor_name, weight in get_default_weights(factor_set).items():
                db.add(FactorWeight(
                    tenant_id=tenant.id,
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

        # ---- Scored Collections ----
        sa_methods = [CollectionMethod.CARD, CollectionMethod.CARD, CollectionMethod.DEBIT_ORDER]
        risk_biases = ["high", "medium", "medium", "low", "low", "low"]

        all_scores: list[tuple[ScoreResult, ScoreRequest]] = []

        # SA: 40 scores
        for i in range(40):
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
                recommended_action=scoring_result.recommended_action,
                model_version=scoring_result.model_version,
                scoring_duration_ms=scoring_result.scoring_duration_ms,
                created_at=scored_at,
            )
            db.add(req)
            db.add(res)
            all_scores.append((res, req))

        # ZM: 20 scores
        for i in range(20):
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
                recommended_action=scoring_result.recommended_action,
                model_version=scoring_result.model_version,
                scoring_duration_ms=scoring_result.scoring_duration_ms,
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
        print("=== SA Tenant ===")
        print(f"  Tenant ID: {sa_tenant.id}")
        print(f"  API Key:   {sa_raw}")
        print(f"  Scores:    40  (CARD + DEBIT_ORDER)")
        print()
        print("=== ZM Tenant ===")
        print(f"  Tenant ID: {zm_tenant.id}")
        print(f"  API Key:   {zm_raw}")
        print(f"  Scores:    20  (MOBILE_MONEY)")
        print()
        print("=== Dashboard Login ===")
        print(f"  Admin:  admin@demo-sa.paypredict.dev  / admin123")
        print(f"  Viewer: viewer@demo-sa.paypredict.dev / viewer123")
        print(f"  Admin:  admin@demo-zm.paypredict.dev  / admin123")
        print(f"  Viewer: viewer@demo-zm.paypredict.dev / viewer123")


if __name__ == "__main__":
    asyncio.run(seed())
