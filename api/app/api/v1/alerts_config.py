"""Dashboard alert configuration endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import DASHBOARD_API_RESPONSES
from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.config import AlertsConfigResponse, AlertsConfigUpdateRequest
from app.services.activity_audit_service import (
    actor_from_user,
    log_activity,
)
from app.services.config_service import (
    get_alerts_config,
    rotate_webhook_secret,
    update_alerts_config,
)

router = APIRouter(
    prefix="/config/alerts",
    tags=["Alert Settings"],
    responses=DASHBOARD_API_RESPONSES,
)


# Fields we compare in the alerts audit diff. `webhook_secret` is
# deliberately excluded — never store secrets (even old ones) in
# audit rows; the `rotate` action is its own log entry.
_ALERT_AUDIT_FIELDS = (
    "high_risk_threshold",
    "webhook_url",
    "slack_webhook_url",
    "email_digest",
    "email_recipients",
)


def _snapshot_alerts(tenant: Tenant) -> dict:
    """Small dict of the fields the alert-config audit diff cares
    about. Kept out of the response schema on purpose — this is
    what lands in the JSONB, not what the client sees."""
    return {
        "high_risk_threshold": tenant.alert_threshold,
        "webhook_url": tenant.webhook_url,
        "slack_webhook_url": tenant.slack_webhook_url,
        "email_digest": (
            tenant.email_digest.value
            if hasattr(tenant.email_digest, "value")
            else tenant.email_digest
        ),
        "email_recipients": list(tenant.email_recipients or []),
    }


def _alerts_diff(before: dict, after: dict) -> tuple[dict, dict]:
    """Return (before_diff, after_diff) restricted to fields that
    actually changed. Empty dicts when nothing meaningful moved
    (caller can decide to skip the audit write entirely)."""
    before_diff: dict = {}
    after_diff: dict = {}
    for field in _ALERT_AUDIT_FIELDS:
        if before[field] != after[field]:
            before_diff[field] = before[field]
            after_diff[field] = after[field]
    return before_diff, after_diff


@router.get("", response_model=AlertsConfigResponse)
async def get_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AlertsConfigResponse:
    return await get_alerts_config(db, user.tenant_id)


@router.put("", response_model=AlertsConfigResponse)
async def update_config(
    req: AlertsConfigUpdateRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AlertsConfigResponse:
    # Snapshot BEFORE. Load the raw tenant so we get the persisted
    # state, not a copy that might have been mutated by another dep.
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )).scalar_one()
    before = _snapshot_alerts(tenant)

    result = await update_alerts_config(db, user.tenant_id, req)

    # Reload post-mutation for the after snapshot.
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == user.tenant_id)
    )).scalar_one()
    after = _snapshot_alerts(tenant)

    before_diff, after_diff = _alerts_diff(before, after)
    if before_diff:
        await log_activity(
            db,
            tenant_id=user.tenant_id,
            entity_type="alert_config",
            entity_id=None,  # tenant-wide, no per-row id
            action="update",
            before=before_diff,
            after=after_diff,
            actor=actor_from_user(user),
            context="alerts_update",
        )

    from app.services.notification_service import EventType, create_notification
    await create_notification(
        db, user.tenant_id, EventType.ALERT_THRESHOLD_CHANGED,
        metadata={"actor_name": user.name},
        actor_id=user.id,
    )
    await db.commit()
    return result


@router.post("/regenerate-secret", response_model=AlertsConfigResponse)
async def regenerate_secret(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AlertsConfigResponse:
    """Rotate the tenant's webhook signing secret. The previous secret is
    immediately invalidated — any in-flight webhooks signed with the old
    secret will fail signature verification on the receiver."""
    result = await rotate_webhook_secret(db, user.tenant_id)
    # No before/after values — never persist the secret (even the old
    # one) in an audit row. The event itself is what compliance cares
    # about: someone rotated on this date.
    await log_activity(
        db,
        tenant_id=user.tenant_id,
        entity_type="webhook_secret",
        entity_id=None,
        action="rotate",
        before=None,
        after=None,
        actor=actor_from_user(user),
        context="webhook_secret_rotate",
    )
    await db.commit()
    return result
