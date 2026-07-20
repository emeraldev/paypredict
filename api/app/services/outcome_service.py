import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outcome import FailureCategory, Outcome, OutcomeStatus
from app.models.score_request import ScoreRequest
from app.models.score_result import ScoreResult
from app.models.tenant import Tenant
from app.schemas.outcome import OutcomeRequest, OutcomeResponse

# Map failure reasons to categories
HARD_DECLINE_REASONS = {
    "card_cancelled", "card_lost", "stolen", "account_closed",
    "invalid_card", "wallet_closed",
}
SOFT_DECLINE_REASONS = {
    "insufficient_funds", "do_not_honour", "exceeded_limit",
    "general_decline", "wallet_empty",
}


async def record_outcome(
    request: OutcomeRequest,
    tenant: Tenant,
    db: AsyncSession,
) -> OutcomeResponse:
    """Record a collection outcome and link to score if provided."""

    # Resolve score_result_id. Two paths:
    #  1. Lender sent an explicit score_id — link to that.
    #  2. Lender omitted score_id — back-link to the most recent
    #     un-outcomed ScoreResult with the same collection_id under this
    #     tenant. Lets API integrators omit the field and lets the
    #     dashboard "Report outcome" form work even if it doesn't have
    #     the score_id at hand. If no match, the outcome is recorded
    #     unlinked (analytics will skip it).
    linked_score_id: uuid.UUID | None = None
    if request.score_id:
        result = await db.execute(
            select(ScoreResult).where(
                ScoreResult.id == request.score_id,
                ScoreResult.tenant_id == tenant.id,
            )
        )
        score_result = result.scalar_one_or_none()
        if score_result:
            linked_score_id = score_result.id
    else:
        linked_score_id = await _lookup_unmatched_score(
            db, tenant.id, request.collection_id
        )

    # Determine failure category
    failure_category = None
    if request.failure_reason:
        reason = request.failure_reason.lower()
        if reason in HARD_DECLINE_REASONS:
            failure_category = FailureCategory.HARD_DECLINE
        elif reason in SOFT_DECLINE_REASONS:
            failure_category = FailureCategory.SOFT_DECLINE
        else:
            failure_category = FailureCategory.TECHNICAL

    now = datetime.now(timezone.utc)
    outcome = Outcome(
        id=uuid.uuid4(),
        score_result_id=linked_score_id,
        tenant_id=tenant.id,
        external_collection_id=request.collection_id,
        outcome=OutcomeStatus(request.outcome),
        failure_reason=request.failure_reason,
        failure_category=failure_category,
        amount_collected=request.amount_collected,
        attempted_at=request.attempted_at,
        reported_at=now,
    )
    db.add(outcome)
    await db.flush()

    return OutcomeResponse(
        outcome_id=outcome.id,
        linked_score_id=linked_score_id,
        received_at=now,
    )


async def _lookup_unmatched_score(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    collection_id: str,
) -> uuid.UUID | None:
    """Find the most recent un-outcomed ScoreResult for a given collection_id.

    "Un-outcomed" = no Outcome row points to that ScoreResult yet. We pick the
    most recent so re-scored collections (lenders sometimes score the same
    collection multiple times before attempting) get linked to the latest
    prediction, not an older one.
    """
    stmt = (
        select(ScoreResult.id)
        .join(ScoreRequest, ScoreRequest.id == ScoreResult.score_request_id)
        .outerjoin(Outcome, Outcome.score_result_id == ScoreResult.id)
        .where(
            ScoreRequest.tenant_id == tenant_id,
            ScoreRequest.external_collection_id == collection_id,
            Outcome.id.is_(None),
        )
        .order_by(ScoreResult.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_outcome(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    outcome_id: uuid.UUID,
) -> bool:
    """Delete an outcome for the given tenant. Returns True if deleted, False
    if no row matched (404 path). The tenant filter prevents cross-tenant
    deletion via id-guessing."""
    result = await db.execute(
        select(Outcome).where(
            Outcome.id == outcome_id,
            Outcome.tenant_id == tenant_id,
        )
    )
    outcome = result.scalar_one_or_none()
    if outcome is None:
        return False
    await db.delete(outcome)
    await db.flush()
    return True
