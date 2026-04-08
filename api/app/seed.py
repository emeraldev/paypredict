"""Seed script for local development and demos.

Usage: python -m app.seed
"""

import asyncio
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select

from app.database import async_session, engine, Base
from app.models.tenant import FactorSet, Market, Plan, Tenant
from app.models.api_key import ApiKey
from app.models.factor_weight import FactorWeight
from app.models.user import User, UserRole
from app.scoring.registry import get_default_weights


def generate_api_key(prefix: str) -> tuple[str, str]:
    """Generate an API key and return (raw_key, hashed_key)."""
    raw = prefix + secrets.token_urlsafe(32)
    hashed = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return raw, hashed


async def seed() -> None:
    async with async_session() as db:
        # Check if already seeded
        result = await db.execute(select(Tenant).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        now = datetime.now(timezone.utc)

        # --- Tenant 1: SA BNPL ---
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
        db.add(sa_tenant)

        # --- Tenant 2: Zambia MoMo ---
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
        db.add(zm_tenant)

        # --- API Keys ---
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

        # --- Factor Weights (defaults) ---
        for tenant, factor_set in [
            (sa_tenant, "CARD_DEBIT"),
            (zm_tenant, "MOBILE_WALLET"),
        ]:
            defaults = get_default_weights(factor_set)
            for factor_name, weight in defaults.items():
                db.add(FactorWeight(
                    tenant_id=tenant.id,
                    factor_name=factor_name,
                    weight=weight,
                    updated_at=now,
                ))

        # --- Admin Users ---
        admin_password = bcrypt.hashpw(
            b"admin123", bcrypt.gensalt()
        ).decode("utf-8")

        db.add(User(
            tenant_id=sa_tenant.id,
            email="admin@demo-sa.paypredict.dev",
            name="SA Admin",
            password_hash=admin_password,
            role=UserRole.ADMIN,
        ))

        db.add(User(
            tenant_id=zm_tenant.id,
            email="admin@demo-zm.paypredict.dev",
            name="ZM Admin",
            password_hash=admin_password,
            role=UserRole.ADMIN,
        ))

        await db.commit()

        print("Seed completed successfully!")
        print()
        print("=== SA Tenant ===")
        print(f"  Tenant ID: {sa_tenant.id}")
        print(f"  API Key:   {sa_raw}")
        print()
        print("=== ZM Tenant ===")
        print(f"  Tenant ID: {zm_tenant.id}")
        print(f"  API Key:   {zm_raw}")
        print()
        print("Dashboard login: admin@demo-sa.paypredict.dev / admin123")
        print("                 admin@demo-zm.paypredict.dev / admin123")


if __name__ == "__main__":
    asyncio.run(seed())
