"""Dashboard config service — api-keys CRUD, team CRUD, alerts GET/PUT.

All queries scoped to tenant_id for row-level isolation.
"""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)

import bcrypt
from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.api_key_service import mint_key

from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.config import (
    AlertsConfigResponse,
    AlertsConfigUpdateRequest,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListItem,
    ApiKeyListResponse,
    ApiKeyToggleRequest,
    TeamInviteRequest,
    TeamListResponse,
    TeamMemberItem,
    TeamUpdateRequest,
)
from app.services.auth_service import hash_password


# ==================== API Keys ====================

async def list_api_keys(
    db: AsyncSession, tenant_id: uuid.UUID
) -> ApiKeyListResponse:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.tenant_id == tenant_id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return ApiKeyListResponse(
        items=[
            ApiKeyListItem(
                id=k.id,
                prefix=k.key_prefix,
                label=k.label,
                is_active=k.is_active,
                last_used_at=k.last_used_at,
                created_at=k.created_at,
            )
            for k in keys
        ]
    )


_MINT_MAX_ATTEMPTS = 3


async def create_api_key(
    db: AsyncSession, tenant_id: uuid.UUID, req: ApiKeyCreateRequest
) -> ApiKeyCreateResponse:
    """Mint a new API key in the format described in `api_key_service`.

    Retries on IntegrityError against `uq_api_keys_lookup_id` — a 48-bit
    collision is astronomically unlikely (~2^-24 at a billion active
    keys), but "astronomical" isn't "never" and the alternative is a
    500 to the customer. Cap the loop so a stuck DB doesn't spin.
    """
    for attempt in range(_MINT_MAX_ATTEMPTS):
        raw_key, lookup_id, display_prefix = mint_key("pk_live_")
        key_hash = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        api_key = ApiKey(
            tenant_id=tenant_id,
            lookup_id=lookup_id,
            key_hash=key_hash,
            key_prefix=display_prefix,
            label=req.label,
            is_active=True,
        )
        db.add(api_key)
        try:
            await db.flush()
        except IntegrityError:
            # lookup_id collision — retry with a fresh id. Roll back
            # the failed row so the session is usable again.
            await db.rollback()
            if attempt == _MINT_MAX_ATTEMPTS - 1:
                raise
            continue

        return ApiKeyCreateResponse(
            id=api_key.id,
            key=raw_key,
            prefix=display_prefix,
            label=req.label,
        )

    # Unreachable — the loop either returns or re-raises.
    raise RuntimeError("mint_key retry loop exited without a result")


async def toggle_api_key(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    key_id: uuid.UUID,
    req: ApiKeyToggleRequest,
) -> ApiKeyListItem:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id)
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = req.is_active
    await db.flush()

    return ApiKeyListItem(
        id=key.id,
        prefix=key.key_prefix,
        label=key.label,
        is_active=key.is_active,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
    )


async def delete_api_key(
    db: AsyncSession, tenant_id: uuid.UUID, key_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id)
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(key)


# ==================== Team ====================

async def list_team(
    db: AsyncSession, tenant_id: uuid.UUID
) -> TeamListResponse:
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.asc())
    )
    users = result.scalars().all()
    return TeamListResponse(
        items=[
            TeamMemberItem(
                id=u.id,
                email=u.email,
                name=u.name,
                role=u.role,
                last_login_at=u.last_login_at,
                created_at=u.created_at,
            )
            for u in users
        ]
    )


async def invite_member(
    db: AsyncSession, tenant_id: uuid.UUID, req: TeamInviteRequest
) -> TeamMemberItem:
    # Check email uniqueness
    existing = await db.execute(
        select(User).where(User.email == req.email.lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")

    user = User(
        tenant_id=tenant_id,
        email=req.email.lower(),
        name=req.name,
        password_hash=hash_password(req.password),
        role=req.role,
    )
    db.add(user)
    await db.flush()

    return TeamMemberItem(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


async def update_member_role(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    req: TeamUpdateRequest,
) -> TeamMemberItem:
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = req.role
    await db.flush()

    return TeamMemberItem(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


async def remove_member(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)


# ==================== Alerts ====================

import secrets as _secrets


def _generate_webhook_secret() -> str:
    """Generate a new webhook signing secret. The "whsec_" prefix mirrors
    the convention used by Stripe and other webhook-signing platforms so
    leaked secrets are easy to identify in code search/grep."""
    return "whsec_" + _secrets.token_urlsafe(32)


def _to_alerts_response(tenant: Tenant) -> AlertsConfigResponse:
    return AlertsConfigResponse(
        high_risk_threshold=tenant.alert_threshold,
        webhook_url=tenant.webhook_url,
        webhook_secret=tenant.webhook_secret,
        slack_webhook_url=tenant.slack_webhook_url,
        email_digest=tenant.email_digest,
        email_recipients=tenant.email_recipients,
    )


async def get_alerts_config(
    db: AsyncSession, tenant_id: uuid.UUID
) -> AlertsConfigResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()
    return _to_alerts_response(tenant)


async def update_alerts_config(
    db: AsyncSession, tenant_id: uuid.UUID, req: AlertsConfigUpdateRequest
) -> AlertsConfigResponse:
    """Update alert config, supporting explicit-null to CLEAR a value.

    Before the M4 fix this used `if req.field is not None`, which conflated
    "caller omitted the field" with "caller sent null to clear it". A
    tenant sending `{"webhook_url": null}` to revoke a leaked webhook
    got a 200 and no change — silent revocation failure. Now we use
    `model_dump(exclude_unset=True)`, which yields only the keys the
    caller actually sent; a `null` value clears the column, a missing
    key leaves it alone.

    Cleared destinations (webhook_url, slack_webhook_url, email_recipients)
    are logged so the audit trail records the revocation intent — the
    whole point of clearing a leaked destination is to be able to prove
    later that you did.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()

    provided = req.model_dump(exclude_unset=True)

    # high_risk_threshold rejects null via the schema (float | None with
    # ge/le only accepts a real number); no clear semantics.
    if "high_risk_threshold" in provided and provided["high_risk_threshold"] is not None:
        tenant.alert_threshold = provided["high_risk_threshold"]

    # For each destination-shaped field: allow both set (str/list) and
    # explicit-null (clear). Log the clear so a leaked webhook has an
    # audit trail.
    if "webhook_url" in provided:
        if provided["webhook_url"] is None and tenant.webhook_url:
            _logger.info(
                "alerts.webhook_url cleared for tenant %s (previous=%s)",
                tenant_id, tenant.webhook_url,
            )
        tenant.webhook_url = provided["webhook_url"]

    if "slack_webhook_url" in provided:
        if provided["slack_webhook_url"] is None and tenant.slack_webhook_url:
            _logger.info(
                "alerts.slack_webhook_url cleared for tenant %s (previous=%s)",
                tenant_id, tenant.slack_webhook_url,
            )
        tenant.slack_webhook_url = provided["slack_webhook_url"]

    if "email_digest" in provided and provided["email_digest"] is not None:
        # `email_digest` is an enum with OFF as the "no digest" value —
        # explicit null is meaningless. Follow the previous set-only shape.
        tenant.email_digest = provided["email_digest"]

    if "email_recipients" in provided:
        # None or [] both mean "no recipients." Log if this represents a clear.
        was_populated = bool(tenant.email_recipients)
        if provided["email_recipients"] in (None, []) and was_populated:
            _logger.info(
                "alerts.email_recipients cleared for tenant %s (previous=%s)",
                tenant_id, tenant.email_recipients,
            )
        # Persist as an empty list rather than NULL to match the ARRAY column.
        tenant.email_recipients = provided["email_recipients"] or []

    await db.flush()

    return _to_alerts_response(tenant)


async def rotate_webhook_secret(
    db: AsyncSession, tenant_id: uuid.UUID
) -> AlertsConfigResponse:
    """Generate a new webhook secret and invalidate the previous one."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()
    tenant.webhook_secret = _generate_webhook_secret()
    await db.flush()
    return _to_alerts_response(tenant)
