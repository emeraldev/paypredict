"""Find the optimal collection date within a window around the original.

Re-runs the existing `ScoringEngine` against each candidate date in
`[original - SEARCH_WINDOW_DAYS, original + SEARCH_WINDOW_DAYS]` and
picks the one with the lowest predicted risk. The date-dependent factors
(DayOfMonthVsPayday, SalaryCycleAlignment) are what make different
candidates score differently — date-independent factors return the same
number for every candidate, so the search reduces to "find the date that
minimises those factors' weighted contribution."

Design notes:
  - Grid search across daily granularity. Latency budget at the
    documented ±14 days is ~30ms per request (29 extra evaluations);
    closed-form analysis would be marginally faster but couples the
    optimiser to the specific factor classes.
  - Past dates are skipped (`today` is injectable so tests don't depend
    on wall-clock).
  - Original date is not in the candidate set — `should_shift` requires
    a strictly different date.
  - Threshold avoids returning shifts that are technically lower-risk
    but operationally noise.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.models.score_request import CollectionMethod
from app.scoring.engine import ScoringEngine


SEARCH_WINDOW_DAYS = 14
SHIFT_THRESHOLD = 0.10


@dataclass(frozen=True)
class TimingRecommendation:
    """Outcome of the search.

    `should_shift` is True iff we found a strictly better date in the
    window and the improvement is at least `SHIFT_THRESHOLD`. When
    False, the lender should collect on the original date.
    """

    should_shift: bool
    recommended_date: date | None
    recommended_score: float | None
    score_improvement: float  # 0.0 when no shift is recommended


def optimise_collection_date(
    engine: ScoringEngine,
    *,
    factor_set: str,
    customer_data: dict,
    collection_data: dict,
    collection_method: CollectionMethod,
    original_score: float,
    custom_weights: dict[str, float] | None = None,
    today: date | None = None,
) -> TimingRecommendation:
    """Search ±SEARCH_WINDOW_DAYS around `collection_due_date` and return
    the best candidate.

    `today` is injectable for deterministic tests; defaults to
    `date.today()` in production.
    """
    original_date = collection_data["collection_due_date"]
    floor = today if today is not None else date.today()

    best_date = original_date
    best_score = original_score

    for delta in range(-SEARCH_WINDOW_DAYS, SEARCH_WINDOW_DAYS + 1):
        if delta == 0:
            continue
        candidate = original_date + timedelta(days=delta)
        if candidate < floor:
            continue

        result = engine.score(
            factor_set=factor_set,
            customer_data=customer_data,
            collection_data={**collection_data, "collection_due_date": candidate},
            custom_weights=custom_weights,
            collection_method=collection_method,
        )
        if result.score < best_score:
            best_date = candidate
            best_score = result.score

    improvement = round(original_score - best_score, 4)
    should_shift = best_date != original_date and improvement >= SHIFT_THRESHOLD

    return TimingRecommendation(
        should_shift=should_shift,
        recommended_date=best_date if should_shift else None,
        recommended_score=round(best_score, 4) if should_shift else None,
        score_improvement=improvement if should_shift else 0.0,
    )
