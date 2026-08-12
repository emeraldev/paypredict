"""Outcome endpoints — report (lender, API key) + list (dashboard, JWT).

Split by tag for OpenAPI grouping; the docs filter at the schema level keeps
the dashboard endpoint out of the public Swagger UI.
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import (
    DASHBOARD_API_RESPONSES,
    LENDER_API_RESPONSES,
    NOT_FOUND_RESPONSES,
)
from app.database import get_db
from app.dependencies import (
    enforce_rate_limit_or_jwt_write,
    get_current_user,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.outcome import OutcomeRequest, OutcomeResponse
from app.schemas.outcomes_list import OutcomesListResponse
from app.services.activity_audit_service import (
    actor_from_user,
    log_activity,
)
from app.services.outcome_service import delete_outcome, record_outcome
from app.services.outcomes_service import list_outcomes

router = APIRouter()


# ---- Lender-facing (API key auth) -------------------------------------------


@router.post(
    "/outcomes",
    response_model=OutcomeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Outcomes"],
    responses=LENDER_API_RESPONSES,
)
async def report_outcome(
    request: OutcomeRequest,
    # Dual-auth WRITE: API key (rate-limited, same as before) OR dashboard
    # JWT restricted to ADMIN or MANAGER (rate-limit-bypassed, used by the
    # "Report outcome" form in the risk-detail drawer). Pre-M2 this used
    # `enforce_rate_limit_or_jwt` and any VIEWER JWT could persist outcome
    # rows — outcomes feed the labelled ML dataset, so a VIEWER-generated
    # outcome silently corrupts training data.
    tenant: Tenant = Depends(enforce_rate_limit_or_jwt_write),
    db: AsyncSession = Depends(get_db),
) -> OutcomeResponse:
    """Report the result of a collection attempt."""
    return await record_outcome(request, tenant, db)


# ---- Dashboard-facing (JWT session auth) ------------------------------------


@router.get(
    "/outcomes",
    response_model=OutcomesListResponse,
    tags=["Dashboard Outcomes"],
    responses=DASHBOARD_API_RESPONSES,
)
async def outcomes_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    outcome: str | None = Query(None, pattern="^(SUCCESS|FAILED)$"),
    match: str | None = Query(None, pattern="^(MATCHED|MISMATCHED)$"),
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort_by: str = Query(
        "attempted_at",
        pattern="^(attempted_at|score|collection_amount)$",
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OutcomesListResponse:
    """List outcomes with prediction match indicators and aggregate stats.

    Stats reflect the full filtered dataset, not just the current page.
    """
    return await list_outcomes(
        db,
        user.tenant_id,
        page=page,
        page_size=page_size,
        outcome_status=outcome,
        match_filter=match,
        search=search,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.delete(
    "/outcomes/{outcome_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Dashboard Outcomes"],
    responses={**DASHBOARD_API_RESPONSES, **NOT_FOUND_RESPONSES},
)
async def remove_outcome(
    outcome_id: UUID,
    # Dashboard-only — JWT required. We don't expose this to API key callers
    # because deleting outcomes is destructive and shouldn't be reachable from
    # a lender's automation by accident. Same auth rule as the rest of the
    # /v1/outcomes GET surface.
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete an outcome. Clerks use this to fix a mistaken entry;
    the row survives with `deleted_at` set so the labelled ML training
    dataset stays intact. Read endpoints filter deleted rows out."""
    outcome = await delete_outcome(db, user.tenant_id, outcome_id, deleted_by=user.id)
    if outcome is None:
        raise HTTPException(status_code=404, detail="Outcome not found")

    await log_activity(
        db,
        tenant_id=user.tenant_id,
        entity_type="outcome",
        entity_id=outcome_id,
        action="delete",
        before={
            "outcome": outcome.outcome.value,
            "collection_id": outcome.external_collection_id,
            "failure_reason": outcome.failure_reason,
        },
        after=None,
        actor=actor_from_user(user),
        context="outcome_soft_delete",
    )
    await db.commit()
