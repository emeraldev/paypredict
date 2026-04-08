import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outcome import FailureCategory, Outcome, OutcomeStatus
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

    # Resolve score_result_id if score_id provided
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
        external_collection_id=request.external_collection_id,
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
