"""Factor weight configuration.

Weights are stored per collection method — every scoring request already
carries `collection_method`, and the engine uses that to pick which
factor bundle applies. A single tenant that collects via multiple
methods (card + debit order, or payroll + card) tunes each independently.

GET returns a grouped view: one entry per method the tenant actually
uses (has scored at least once OR has saved custom weights for). A
payroll-only lender sees one entry, not four.

PUT touches ONE method at a time — a payload for CARD leaves the
tenant's PAYROLL weights untouched. Weights must sum to 1.0 (±0.01) and
every factor name must belong to the method's bundle.

Accepts either an API key (rate-limited) or a JWT (ADMIN only).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.docs_config import LENDER_API_RESPONSES
from app.database import get_db
from app.dependencies import (
    enforce_rate_limit_or_jwt,
    get_current_user,
    require_admin,
    session_security,
)
from app.models.score_request import CollectionMethod
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.weight_change_log import WeightChangeActorType
from app.schemas.config import (
    WeightChangeLogEntry,
    WeightChangeLogResponse,
    WeightsAddMethodRequest,
    WeightsFactorEntry,
    WeightsMethodEntry,
    WeightsResponse,
    WeightsUpdateRequest,
)
from app.scoring.registry import (
    FACTOR_DESCRIPTIONS,
    FACTOR_LABELS,
    METHOD_LABELS,
    get_factors_for_method,
)
from app.services.weight_audit_service import (
    WeightChangeActor,
    list_weight_changes,
)
from app.services.weights_service import (
    add_method_with_defaults,
    get_effective_weights_for_method,
    list_configured_methods,
    upsert_weights_for_method,
)

router = APIRouter(prefix="/config", tags=["Configuration"], responses=LENDER_API_RESPONSES)

# Second router for admin-only, dashboard-only endpoints under the same
# /config prefix. Tagged separately so the compliance audit endpoints
# stay out of the public Swagger UI (which filters on router tags).
history_router = APIRouter(prefix="/config", tags=["Weight History"])


WEIGHT_SUM_TOLERANCE = 0.01


def _actor_from_user(user: User | None) -> WeightChangeActor:
    """Build the audit-log actor descriptor from the resolved auth.

    JWT path: user is present, log as `user` with denormalized name.
    API-key path: user is None, log as `api_key` with a generic name
    (we deliberately do NOT link to the api_keys.id here — the audit
    should stay readable if the key is later revoked).
    """
    if user is not None:
        return WeightChangeActor(
            type=WeightChangeActorType.USER, id=user.id, name=user.name
        )
    return WeightChangeActor(
        type=WeightChangeActorType.API_KEY, id=None, name="API key"
    )


async def _build_response(
    db: AsyncSession, tenant: Tenant
) -> WeightsResponse:
    """Compose the grouped GET body from persisted rows + defaults."""
    methods = await list_configured_methods(db, tenant.id)
    entries: list[WeightsMethodEntry] = []

    for method in methods:
        effective = await get_effective_weights_for_method(db, tenant.id, method)
        # Preserve bundle-registry order — the dashboard renders sliders in
        # the order the API returns.
        ordered_names = list(get_factors_for_method(method).keys())
        factors = [
            WeightsFactorEntry(
                factor_name=name,
                label=FACTOR_LABELS.get(name, name),
                description=FACTOR_DESCRIPTIONS.get(name, ""),
                weight=effective[name],
            )
            for name in ordered_names
        ]
        entries.append(
            WeightsMethodEntry(
                collection_method=method,
                method_label=METHOD_LABELS[method],
                factors=factors,
                total_weight=round(sum(f.weight for f in factors), 4),
            )
        )

    return WeightsResponse(methods=entries)


@router.get("/weights", response_model=WeightsResponse)
async def get_weights(
    tenant: Tenant = Depends(enforce_rate_limit_or_jwt),
    db: AsyncSession = Depends(get_db),
) -> WeightsResponse:
    """Return current factor weights grouped by collection method.

    Only methods this tenant actually uses appear in the response.
    """
    return await _build_response(db, tenant)


@router.put("/weights", response_model=WeightsResponse)
async def update_weights(
    body: WeightsUpdateRequest,
    tenant: Tenant = Depends(enforce_rate_limit_or_jwt),
    credentials: HTTPAuthorizationCredentials | None = Security(session_security),
    db: AsyncSession = Depends(get_db),
) -> WeightsResponse:
    """Update the tenant's factor weights for ONE collection method.

    Body:
      {
        "collection_method": "PAYROLL",
        "weights": { "threshold_headroom": 0.30, ... }
      }

    ADMIN-only when called via JWT; API-key callers are implicitly
    trusted (the key belongs to the tenant).
    """
    method = body.collection_method

    # Validate every submitted factor name belongs to this method's bundle.
    # Cheap upfront check keeps the DB out of the failure mode.
    valid_factors = set(get_factors_for_method(method).keys())
    unknown = set(body.weights.keys()) - valid_factors
    if unknown:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Unknown factor names for {method.value}",
                "unknown_factors": sorted(unknown),
                "valid_factors": sorted(valid_factors),
            },
        )

    total = sum(body.weights.values())
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Weights for {method.value} must sum to 1.0 "
                f"(±{WEIGHT_SUM_TOLERANCE}); got {round(total, 4)}"
            ),
        )

    # Identify the acting user when the call came in via JWT so the
    # notification has a real actor. API-key callers are implicitly
    # trusted (the key belongs to the tenant); JWT callers must be ADMIN.
    actor_user: User | None = None
    if credentials and not credentials.credentials.startswith("pk_"):
        actor_user = await get_current_user(credentials, db)
        if actor_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Admin role required to update factor weights",
            )

    await upsert_weights_for_method(
        db,
        tenant.id,
        method,
        body.weights,
        updated_by=actor_user.id if actor_user else None,
        actor=_actor_from_user(actor_user),
    )

    from app.services.notification_service import EventType, create_notification

    await create_notification(
        db,
        tenant.id,
        EventType.WEIGHTS_UPDATED,
        metadata={
            "actor_name": actor_user.name if actor_user else "API key",
            "collection_method": method.value,
            "method_label": METHOD_LABELS[method],
        },
        actor_id=actor_user.id if actor_user else None,
    )

    await db.commit()
    return await _build_response(db, tenant)


@router.post("/weights/methods", response_model=WeightsResponse)
async def add_weights_method(
    body: WeightsAddMethodRequest,
    tenant: Tenant = Depends(enforce_rate_limit_or_jwt),
    credentials: HTTPAuthorizationCredentials | None = Security(session_security),
    db: AsyncSession = Depends(get_db),
) -> WeightsResponse:
    """Opt into weight configuration for a new collection method.

    Seeds default weights for the method so the dashboard exposes a tab
    for it before the tenant has scored their first collection with
    that method. Useful when a lender is preparing to expand into a
    new collection method and wants to tune weights up front.

    Idempotent — repeating the call for a method that already has
    weights is a no-op that returns the same current state.

    ADMIN-only when called via JWT; API-key callers are trusted (the
    key belongs to the tenant).
    """
    method = body.collection_method

    actor_user: User | None = None
    if credentials and not credentials.credentials.startswith("pk_"):
        actor_user = await get_current_user(credentials, db)
        if actor_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Admin role required to add a collection method",
            )

    created = await add_method_with_defaults(
        db,
        tenant.id,
        method,
        updated_by=actor_user.id if actor_user else None,
        actor=_actor_from_user(actor_user),
    )

    if created:
        from app.services.notification_service import EventType, create_notification

        await create_notification(
            db,
            tenant.id,
            EventType.WEIGHTS_UPDATED,
            metadata={
                "actor_name": actor_user.name if actor_user else "API key",
                "collection_method": method.value,
                "method_label": METHOD_LABELS[method],
                "action": "method_added",
            },
            actor_id=actor_user.id if actor_user else None,
        )

    await db.commit()
    return await _build_response(db, tenant)


@history_router.get(
    "/weights/history",
    response_model=WeightChangeLogResponse,
)
async def list_weights_history(
    collection_method: CollectionMethod | None = Query(
        None,
        description="Filter to a single collection method (CARD, DEBIT_ORDER, ...).",
    ),
    factor_name: str | None = Query(
        None,
        description="Filter to a single factor (snake_case name from the bundle).",
    ),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> WeightChangeLogResponse:
    """Paginated audit trail of every weight change on this tenant.

    Admin-only. Answers the compliance question "who changed which
    factor and when" — the `factor_weights` table itself is
    upsert-in-place and loses that history. Ordered most-recent-first;
    filterable by method or factor.
    """
    rows, total = await list_weight_changes(
        db,
        user.tenant_id,
        limit=limit,
        offset=offset,
        collection_method=collection_method,
        factor_name=factor_name,
    )

    items = [
        WeightChangeLogEntry(
            id=row.id,
            collection_method=CollectionMethod(row.collection_method),
            method_label=METHOD_LABELS.get(
                CollectionMethod(row.collection_method), row.collection_method
            ),
            factor_name=row.factor_name,
            factor_label=FACTOR_LABELS.get(row.factor_name, row.factor_name),
            old_weight=row.old_weight,
            new_weight=row.new_weight,
            actor_type=row.actor_type.value,
            actor_name=row.actor_name,
            context=row.context,
            changed_at=row.changed_at,
        )
        for row in rows
    ]
    return WeightChangeLogResponse(
        items=items, total=total, limit=limit, offset=offset
    )
