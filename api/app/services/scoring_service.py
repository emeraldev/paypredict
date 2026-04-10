import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.factor_weight import FactorWeight
from app.models.score_request import CollectionCurrency, CollectionMethod, ScoreRequest
from app.models.score_result import RiskLevel, ScoreResult
from app.models.tenant import Tenant
from app.schemas.score import ScoreRequest as ScoreRequestSchema, ScoreResponse, FactorBreakdown
from app.scoring.engine import ScoringEngine

engine = ScoringEngine()


async def score_collection(
    request: ScoreRequestSchema,
    tenant: Tenant,
    db: AsyncSession,
) -> ScoreResponse:
    """Score a single collection and persist the request + result."""

    # Load tenant's custom weights
    custom_weights = await _load_custom_weights(tenant.id, db)

    # Prepare data dicts for the engine
    customer_data = request.customer_data.model_dump()
    collection_data = {
        "collection_amount": request.collection_amount,
        "collection_due_date": request.collection_due_date,
        "collection_method": request.collection_method,
        "collection_currency": request.collection_currency,
    }

    # Run scoring engine with collection method filtering
    collection_method = CollectionMethod(request.collection_method)
    result = engine.score(
        factor_set=tenant.factor_set.value,
        customer_data=customer_data,
        collection_data=collection_data,
        custom_weights=custom_weights if custom_weights else None,
        collection_method=collection_method,
    )

    # Persist ScoreRequest
    score_request = ScoreRequest(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        external_customer_id=request.external_customer_id,
        external_collection_id=request.external_collection_id,
        collection_amount=request.collection_amount,
        collection_currency=CollectionCurrency(request.collection_currency),
        collection_due_date=request.collection_due_date,
        collection_method=CollectionMethod(request.collection_method),
        request_payload=request.model_dump(mode="json"),
    )
    db.add(score_request)

    # Persist ScoreResult
    score_result = ScoreResult(
        id=uuid.uuid4(),
        score_request_id=score_request.id,
        tenant_id=tenant.id,
        score=result.score,
        risk_level=RiskLevel(result.risk_level),
        factors={
            "evaluated": [
                {
                    "factor_name": f.factor_name,
                    "raw_score": f.raw_score,
                    "weight": f.weight,
                    "weighted_score": f.weighted_score,
                    "explanation": f.explanation,
                }
                for f in result.factors
            ],
            "skipped": result.skipped_factors,
        },
        recommended_action=result.recommended_action,
        model_version=result.model_version,
        scoring_duration_ms=result.scoring_duration_ms,
    )
    db.add(score_result)
    await db.flush()

    return ScoreResponse(
        score_id=score_result.id,
        score=result.score,
        risk_level=result.risk_level,
        recommended_action=result.recommended_action,
        recommended_collection_date=None,
        factors=[
            FactorBreakdown(
                factor=f.factor_name,
                raw_score=f.raw_score,
                weight=f.weight,
                weighted_score=f.weighted_score,
                explanation=f.explanation,
            )
            for f in result.factors
        ],
        skipped_factors=result.skipped_factors,
        model_version=result.model_version,
        scored_at=datetime.now(timezone.utc),
        scoring_duration_ms=result.scoring_duration_ms,
    )


async def _load_custom_weights(
    tenant_id: uuid.UUID, db: AsyncSession
) -> dict[str, float]:
    """Load tenant's custom factor weights from the database."""
    result = await db.execute(
        select(FactorWeight).where(FactorWeight.tenant_id == tenant_id)
    )
    weights = result.scalars().all()
    return {w.factor_name: w.weight for w in weights}
