"""Dashboard config service — api-keys CRUD, team CRUD, alerts GET/PUT.

All queries scoped to tenant_id for row-level isolation.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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


async def create_api_key(
    db: AsyncSession, tenant_id: uuid.UUID, req: ApiKeyCreateRequest
) -> ApiKeyCreateResponse:
    raw_key = "pk_live_" + secrets.token_urlsafe(32)
    key_hash = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    prefix = raw_key[:8]

    api_key = ApiKey(
        tenant_id=tenant_id,
        key_hash=key_hash,
        key_prefix=prefix,
        label=req.label,
        is_active=True,
    )
    db.add(api_key)
    await db.flush()

    return ApiKeyCreateResponse(
        id=api_key.id,
        key=raw_key,
        prefix=prefix,
        label=req.label,
    )


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

async def get_alerts_config(
    db: AsyncSession, tenant_id: uuid.UUID
) -> AlertsConfigResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()
    return AlertsConfigResponse(
        high_risk_threshold=tenant.alert_threshold,
        webhook_url=tenant.webhook_url,
        slack_webhook_url=tenant.slack_webhook_url,
        email_digest=tenant.email_digest,
        email_recipients=tenant.email_recipients,
    )


async def update_alerts_config(
    db: AsyncSession, tenant_id: uuid.UUID, req: AlertsConfigUpdateRequest
) -> AlertsConfigResponse:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()

    if req.high_risk_threshold is not None:
        tenant.alert_threshold = req.high_risk_threshold
    if req.webhook_url is not None:
        tenant.webhook_url = req.webhook_url
    if req.slack_webhook_url is not None:
        tenant.slack_webhook_url = req.slack_webhook_url
    if req.email_digest is not None:
        tenant.email_digest = req.email_digest
    if req.email_recipients is not None:
        tenant.email_recipients = req.email_recipients

    await db.flush()

    return AlertsConfigResponse(
        high_risk_threshold=tenant.alert_threshold,
        webhook_url=tenant.webhook_url,
        slack_webhook_url=tenant.slack_webhook_url,
        email_digest=tenant.email_digest,
        email_recipients=tenant.email_recipients,
    )
