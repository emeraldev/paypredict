"""Notification service — SINGLE entry point for creating notifications.

Every service that needs to create a notification calls create_notification().
Never insert into the Notification table directly. Templates define all
content (title, message format, severity, link) in one place.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
)
from app.services.query_utils import PaginationMeta, paginate


class EventType(str, Enum):
    # System (automated)
    HIGH_RISK_BATCH = "high_risk_batch"
    COLLECTION_RATE_DROP = "collection_rate_drop"
    PREDICTION_DRIFT = "prediction_drift"
    BACKTEST_COMPLETE = "backtest_complete"
    BULK_SCORING_COMPLETE = "bulk_scoring_complete"
    OUTCOME_SPIKE = "outcome_spike"
    CARD_HEALTH_WARNING = "card_health_warning"
    API_KEY_UNUSED = "api_key_unused"
    # Activity (user actions)
    WEIGHTS_UPDATED = "weights_updated"
    TEAM_MEMBER_INVITED = "team_member_invited"
    TEAM_MEMBER_JOINED = "team_member_joined"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    ALERT_THRESHOLD_CHANGED = "alert_threshold_changed"


# ---- Templates — SINGLE SOURCE OF TRUTH for all notification content ----

_TEMPLATES: dict[EventType, dict] = {
    EventType.HIGH_RISK_BATCH: {
        "category": NotificationCategory.SYSTEM,
        "severity": NotificationSeverity.CRITICAL,
        "title": "High-risk batch detected",
        "message": "{high_risk_count} of {total_count} collections ({percentage:.0%}) scored as high risk — exceeds your {threshold:.0%} threshold",
        "link_to": "/dashboard?risk_level=HIGH",
        "link_label": "View high-risk collections",
    },
    EventType.COLLECTION_RATE_DROP: {
        "category": NotificationCategory.SYSTEM,
        "severity": NotificationSeverity.WARNING,
        "title": "Collection rate dropping",
        "message": "Collection rate dropped to {current_rate:.1%} — down {drop:.1%} from last week",
        "link_to": "/dashboard/analytics",
        "link_label": "View analytics",
    },
    EventType.PREDICTION_DRIFT: {
        "category": NotificationCategory.SYSTEM,
        "severity": NotificationSeverity.WARNING,
        "title": "Prediction accuracy declining",
        "message": "Prediction accuracy dropped to {accuracy:.0%} this week — factor weights may need tuning",
        "link_to": "/dashboard/analytics",
        "link_label": "View prediction accuracy",
    },
    EventType.BACKTEST_COMPLETE: {
        "category": NotificationCategory.SYSTEM,
        "severity": NotificationSeverity.INFO,
        "title": "Backtest complete",
        "message": "Backtest completed — {total_collections} collections scored with {accuracy:.0%} accuracy",
        "link_to": "/dashboard/backtest",
        "link_label": "View backtest results",
    },
    EventType.BULK_SCORING_COMPLETE: {
        "category": NotificationCategory.SYSTEM,
        "severity": NotificationSeverity.INFO,
        "title": "Bulk scoring complete",
        "message": "Bulk scoring complete — {total} collections scored ({high_risk} high risk)",
        "link_to": "/dashboard",
        "link_label": "View scored collections",
    },
    EventType.OUTCOME_SPIKE: {
        "category": NotificationCategory.SYSTEM,
        "severity": NotificationSeverity.WARNING,
        "title": "Failure spike detected",
        "message": "{failure_count} collection failures reported in the last hour — higher than normal",
        "link_to": "/dashboard/outcomes",
        "link_label": "View recent failures",
    },
    EventType.CARD_HEALTH_WARNING: {
        "category": NotificationCategory.SYSTEM,
        "severity": NotificationSeverity.INFO,
        "title": "Cards expiring soon",
        "message": "{card_count} upcoming collections have cards expiring soon — consider proactive outreach",
        "link_to": "/dashboard?risk_level=HIGH",
        "link_label": "View affected collections",
    },
    EventType.API_KEY_UNUSED: {
        "category": NotificationCategory.SYSTEM,
        "severity": NotificationSeverity.INFO,
        "title": "API key inactive",
        "message": "API key '{key_label}' hasn't been used in 30 days",
        "link_to": "/dashboard/settings?tab=api-keys",
        "link_label": "Manage API keys",
    },
    EventType.WEIGHTS_UPDATED: {
        "category": NotificationCategory.ACTIVITY,
        "severity": NotificationSeverity.INFO,
        "title": "Factor weights updated",
        "message": "Factor weights updated by {actor_name}",
        "link_to": "/dashboard/settings?tab=weights",
        "link_label": "View weights",
    },
    EventType.TEAM_MEMBER_INVITED: {
        "category": NotificationCategory.ACTIVITY,
        "severity": NotificationSeverity.INFO,
        "title": "Team member invited",
        "message": "{invitee_name} was invited as {invitee_role} by {actor_name}",
        "link_to": "/dashboard/settings?tab=team",
        "link_label": "View team",
    },
    EventType.TEAM_MEMBER_JOINED: {
        "category": NotificationCategory.ACTIVITY,
        "severity": NotificationSeverity.INFO,
        "title": "Team member joined",
        "message": "{member_name} has joined the team",
        "link_to": "/dashboard/settings?tab=team",
        "link_label": "View team",
    },
    EventType.API_KEY_CREATED: {
        "category": NotificationCategory.ACTIVITY,
        "severity": NotificationSeverity.INFO,
        "title": "API key created",
        "message": "New API key '{key_label}' created by {actor_name}",
        "link_to": "/dashboard/settings?tab=api-keys",
        "link_label": "View API keys",
    },
    EventType.API_KEY_REVOKED: {
        "category": NotificationCategory.ACTIVITY,
        "severity": NotificationSeverity.WARNING,
        "title": "API key revoked",
        "message": "API key '{key_label}' was revoked by {actor_name}",
        "link_to": "/dashboard/settings?tab=api-keys",
        "link_label": "View API keys",
    },
    EventType.ALERT_THRESHOLD_CHANGED: {
        "category": NotificationCategory.ACTIVITY,
        "severity": NotificationSeverity.INFO,
        "title": "Alert settings updated",
        "message": "Alert settings updated by {actor_name}",
        "link_to": "/dashboard/settings?tab=alerts",
        "link_label": "View alert settings",
    },
}

# TODO: Scheduled checks — deferred until real tenants generate enough data.
# These would be Celery Beat tasks that run daily/weekly and call
# create_notification() when thresholds are breached:
#   - check_collection_rate_drop (daily 09:00)
#   - check_prediction_drift (weekly Monday 09:00)
#   - check_card_health_warnings (daily 08:00)
#   - check_unused_api_keys (weekly)


async def create_notification(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    event_type: EventType,
    metadata: dict,
    actor_id: uuid.UUID | None = None,
) -> Notification:
    """Create a notification from a template. This is the ONLY function
    that creates notifications — all services call this."""
    template = _TEMPLATES[event_type]

    try:
        message = template["message"].format(**metadata)
    except KeyError:
        message = template["message"]  # Fallback: raw template

    link_to = template.get("link_to")
    if link_to:
        try:
            link_to = link_to.format(**metadata)
        except KeyError:
            pass

    notification = Notification(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        category=template["category"],
        severity=template["severity"],
        event_type=event_type.value,
        title=template["title"],
        message=message,
        link_to=link_to,
        link_label=template.get("link_label"),
        metadata_=metadata,
        actor_id=actor_id,
        is_read=False,
    )
    db.add(notification)
    await db.flush()
    return notification


async def list_notifications(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    category: str | None = None,
    severity: str | None = None,
) -> tuple[list[dict], PaginationMeta, int]:
    """List notifications newest-first. Returns (items, pagination, unread_count)."""
    query = (
        select(Notification)
        .where(Notification.tenant_id == tenant_id)
        .order_by(Notification.created_at.desc())
    )
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    if category:
        query = query.where(Notification.category == NotificationCategory(category))
    if severity:
        query = query.where(Notification.severity == NotificationSeverity(severity))

    rows, pagination = await paginate(db, query, page, page_size)
    unread = await get_unread_count(db, tenant_id)

    items = []
    for (notification,) in rows:
        item = {
            "id": str(notification.id),
            "category": notification.category.value,
            "severity": notification.severity.value,
            "event_type": notification.event_type,
            "title": notification.title,
            "message": notification.message,
            "link_to": notification.link_to,
            "link_label": notification.link_label,
            "metadata": notification.metadata_,
            "actor": None,
            "is_read": notification.is_read,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
            "created_at": notification.created_at.isoformat(),
        }
        items.append(item)

    return items, pagination, unread


async def get_unread_count(db: AsyncSession, tenant_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.tenant_id == tenant_id, Notification.is_read.is_(False))
    )
    return result.scalar_one()


async def mark_as_read(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    notification_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Mark a single notification as read. Returns True if found."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.tenant_id == tenant_id,
        )
        .values(is_read=True, read_at=now, read_by=user_id)
    )
    return result.rowcount > 0


async def mark_all_read(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    """Mark all unread notifications as read. Returns count updated."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now, read_by=user_id)
    )
    return result.rowcount
