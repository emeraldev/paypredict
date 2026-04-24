"""Alert evaluation and notification service.

Evaluates scoring results against tenant thresholds, creates Alert records,
and sends webhook/Slack notifications when thresholds are breached.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertType
from app.models.tenant import Tenant
from app.services.webhook_service import deliver_webhook, send_slack_alert


async def evaluate_alerts(
    tenant: Tenant,
    scoring_summary: dict,
    db: AsyncSession,
) -> Alert | None:
    """Check if scoring results breach the tenant's alert threshold.

    Called after bulk scoring completes. Creates an Alert record and sends
    notifications if the high-risk percentage exceeds the threshold.

    Returns the Alert if one was created, None otherwise.
    """
    # Refresh tenant from DB to get the latest webhook_url and threshold
    # (the tenant object from get_current_tenant may be stale if config
    # was updated in a different request)
    await db.refresh(tenant)

    high_risk_count = scoring_summary.get("high_risk", 0)
    total = (
        scoring_summary.get("high_risk", 0)
        + scoring_summary.get("medium_risk", 0)
        + scoring_summary.get("low_risk", 0)
    )

    if total == 0:
        return None

    high_risk_pct = high_risk_count / total

    if high_risk_pct <= tenant.alert_threshold:
        return None  # Below threshold

    message = (
        f"{high_risk_count} of {total} collections "
        f"({high_risk_pct:.0%}) scored as high risk — "
        f"exceeds {tenant.alert_threshold:.0%} threshold"
    )

    alert = Alert(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        alert_type=AlertType.HIGH_RISK_BATCH,
        message=message,
        metadata_={
            "high_risk_count": high_risk_count,
            "total": total,
            "percentage": round(high_risk_pct, 3),
            "threshold": tenant.alert_threshold,
        },
        is_read=False,
    )
    db.add(alert)
    await db.flush()

    # Send notifications (best-effort, don't fail the request)
    if tenant.webhook_url:
        await deliver_webhook(
            url=tenant.webhook_url,
            secret="paypredict",  # TODO: per-tenant webhook secret
            event="high_risk_alert",
            payload={
                "alert_id": str(alert.id),
                "message": message,
                "high_risk_count": high_risk_count,
                "total": total,
                "percentage": round(high_risk_pct, 3),
            },
        )

    if tenant.slack_webhook_url:
        await send_slack_alert(tenant.slack_webhook_url, message)

    return alert


async def list_alerts(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 20,
) -> list[dict]:
    """List alerts for a tenant, newest first."""
    query = (
        select(Alert)
        .where(Alert.tenant_id == tenant_id)
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        query = query.where(Alert.is_read.is_(False))

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "alert_type": a.alert_type.value,
            "message": a.message,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat(),
            "metadata": a.metadata_,
        }
        for a in alerts
    ]


async def get_unread_count(
    db: AsyncSession, tenant_id: uuid.UUID
) -> int:
    """Count unread alerts for a tenant."""
    result = await db.execute(
        select(func.count())
        .select_from(Alert)
        .where(Alert.tenant_id == tenant_id, Alert.is_read.is_(False))
    )
    return result.scalar_one()


async def mark_alert_read(
    db: AsyncSession, tenant_id: uuid.UUID, alert_id: uuid.UUID
) -> bool:
    """Mark a single alert as read. Returns True if found."""
    result = await db.execute(
        update(Alert)
        .where(Alert.id == alert_id, Alert.tenant_id == tenant_id)
        .values(is_read=True)
    )
    return result.rowcount > 0


async def mark_all_read(
    db: AsyncSession, tenant_id: uuid.UUID
) -> int:
    """Mark all alerts as read for a tenant. Returns count updated."""
    result = await db.execute(
        update(Alert)
        .where(Alert.tenant_id == tenant_id, Alert.is_read.is_(False))
        .values(is_read=True)
    )
    return result.rowcount
