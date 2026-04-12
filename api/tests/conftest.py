"""Shared test fixtures."""

import uuid
from datetime import date

import bcrypt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.tenant import FactorSet, Market, Plan, Tenant
from app.models.api_key import ApiKey
from app.models.factor_weight import FactorWeight
from app.models.score_request import ScoreRequest
from app.models.score_result import ScoreResult
from app.models.outcome import Outcome
from app.models.user import User, UserRole
from app.scoring.registry import get_default_weights
from app.services.auth_service import hash_password

TEST_API_KEY = "pk_test_unit_test_key_1234567890abcdef"
TEST_API_KEY_HASH = bcrypt.hashpw(
    TEST_API_KEY.encode("utf-8"), bcrypt.gensalt()
).decode("utf-8")

TEST_USER_EMAIL = "demo@paypredict.test"
TEST_USER_PASSWORD = "demo-password-1234"


@pytest_asyncio.fixture
async def db_session():
    """Provide a database session. Creates a fresh engine per test to avoid event loop issues."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def sa_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test SA tenant (cleaned up after test)."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test SA Tenant",
        market=Market.SA,
        factor_set=FactorSet.CARD_DEBIT,
        plan=Plan.STARTER,
        is_active=True,
        alert_threshold=0.20,
    )
    db_session.add(tenant)

    db_session.add(ApiKey(
        tenant_id=tenant.id,
        key_hash=TEST_API_KEY_HASH,
        key_prefix=TEST_API_KEY[:8],
        label="Test Key",
        is_active=True,
    ))

    for factor_name, weight in get_default_weights("CARD_DEBIT").items():
        db_session.add(FactorWeight(
            tenant_id=tenant.id,
            factor_name=factor_name,
            weight=weight,
        ))

    await db_session.commit()

    yield tenant

    # Cleanup
    await db_session.execute(delete(User).where(User.tenant_id == tenant.id))
    await db_session.execute(delete(Outcome).where(Outcome.tenant_id == tenant.id))
    await db_session.execute(delete(ScoreResult).where(ScoreResult.tenant_id == tenant.id))
    await db_session.execute(delete(ScoreRequest).where(ScoreRequest.tenant_id == tenant.id))
    await db_session.execute(delete(FactorWeight).where(FactorWeight.tenant_id == tenant.id))
    await db_session.execute(delete(ApiKey).where(ApiKey.tenant_id == tenant.id))
    await db_session.execute(delete(Tenant).where(Tenant.id == tenant.id))
    await db_session.commit()


@pytest_asyncio.fixture
async def sa_admin_user(sa_tenant: Tenant, db_session: AsyncSession) -> User:
    """Create an ADMIN user for the SA test tenant."""
    user = User(
        tenant_id=sa_tenant.id,
        email=TEST_USER_EMAIL,
        name="Test Admin",
        password_hash=hash_password(TEST_USER_PASSWORD),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    # Eagerly load tenant for downstream usage (auth_service expects it)
    user.tenant = sa_tenant
    return user


@pytest_asyncio.fixture
async def zm_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test ZM tenant (cleaned up after test)."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Test ZM Tenant",
        market=Market.ZM,
        factor_set=FactorSet.MOBILE_WALLET,
        plan=Plan.STARTER,
        is_active=True,
        alert_threshold=0.20,
    )
    db_session.add(tenant)
    await db_session.commit()

    yield tenant

    await db_session.execute(delete(Tenant).where(Tenant.id == tenant.id))
    await db_session.commit()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession):
    """Provide an async HTTP client with the test database session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sa_customer_data() -> dict:
    return {
        "total_payments": 10,
        "successful_payments": 7,
        "last_successful_payment_date": "2026-03-25",
        "average_collection_amount": 1200.00,
        "instalment_number": 4,
        "total_instalments": 6,
        "card_type": "debit",
        "card_expiry_date": "2027-06-30",
        "known_salary_day": 25,
    }


@pytest.fixture
def zm_customer_data() -> dict:
    return {
        "total_payments": 8,
        "successful_payments": 6,
        "wallet_balance_7d_avg": 500.00,
        "wallet_balance_current": 350.00,
        "hours_since_last_inflow": 18,
        "regular_inflow_day": "friday",
        "active_loan_count": 1,
        "transactions_last_7d": 12,
        "transactions_avg_7d": 15,
        "last_airtime_purchase_days_ago": 2,
        "loans_taken_last_90d": 1,
    }


@pytest.fixture
def sa_collection_data() -> dict:
    return {
        "collection_amount": 1500.00,
        "collection_due_date": date(2026, 4, 15),
        "collection_method": "CARD",
        "collection_currency": "ZAR",
    }


@pytest.fixture
def zm_collection_data() -> dict:
    return {
        "collection_amount": 250.00,
        "collection_due_date": date(2026, 4, 14),
        "collection_method": "MOBILE_MONEY",
        "collection_currency": "ZMW",
    }
