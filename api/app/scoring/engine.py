import time
from dataclasses import dataclass, field

from app.models.score_request import CollectionMethod
from app.scoring.registry import (
    get_factors_for_method,
    get_factors_for_set,
)


@dataclass
class FactorResult:
    factor_name: str
    raw_score: float
    weight: float
    weighted_score: float
    explanation: str
    # Short code naming the specific policy rule that fired inside the
    # factor, or None when the score alone tells the story. Set by
    # factors that gate on named business rules (e.g.
    # `ThresholdHeadroom` emits "floor_breach" / "ceiling_breach").
    # The engine populates this from `factor.trigger(...)`.
    trigger: str | None = None


@dataclass
class ScoringResult:
    score: float
    risk_level: str
    recommended_action: str
    factors: list[FactorResult]
    skipped_factors: list[str]
    model_version: str
    scoring_duration_ms: int
    # Full effective weight vector at scoring time, BEFORE re-normalisation.
    # Includes every factor in the bundle (evaluated + skipped) so downstream
    # storage can reconstruct the exact config that produced this score even
    # if some factors were skipped. Populated by the engine on every call;
    # persisted as `ScoreResult.weights_snapshot`.
    weights_snapshot: dict[str, float] = field(default_factory=dict)


class ScoringEngine:
    """Orchestrates factor evaluation and produces a final risk score."""

    def score(
        self,
        factor_set: str | None = None,
        customer_data: dict | None = None,
        collection_data: dict | None = None,
        custom_weights: dict[str, float] | None = None,
        collection_method: CollectionMethod | None = None,
    ) -> ScoringResult:
        """Score a collection.

        The canonical driver is `collection_method` — when provided, the
        engine picks the factor bundle for that method regardless of
        `factor_set`. `factor_set` is kept as a fallback for legacy callers
        (tests, older service code) and will be removed once every call
        site has migrated. At least one of the two must be provided.
        """
        if collection_method is None and factor_set is None:
            raise ValueError(
                "engine.score() requires either collection_method or "
                "factor_set (collection_method preferred)"
            )
        start = time.perf_counter_ns()
        customer_data = customer_data or {}
        collection_data = collection_data or {}

        if collection_method is not None:
            factors = get_factors_for_method(collection_method)
        else:
            factors = get_factors_for_set(factor_set)

        # Employment-status short-circuit (PAYROLL only). A borrower who no
        # longer draws a payslip cannot have a payroll deduction succeed
        # regardless of what the other factors say. Short-circuit BEFORE
        # the factor loop so we neither spend the work nor let a healthy
        # salary + tight headroom produce a misleading MEDIUM on someone
        # who is no longer employed.
        if collection_method == CollectionMethod.PAYROLL:
            override = self._employment_status_override(
                customer_data=customer_data,
                factors=factors,
                custom_weights=custom_weights,
                start_ns=start,
            )
            if override is not None:
                return override

        # Separate applicable and skipped factors
        applicable: list[tuple[str, object, float]] = []
        skipped_factors: list[str] = []
        # Snapshot the pre-normalisation weight for EVERY factor in the
        # bundle (evaluated + skipped) so the caller can persist the
        # exact config that produced this score.
        weights_snapshot: dict[str, float] = {}

        for name, (factor, default_weight) in factors.items():
            weight = (custom_weights or {}).get(name, default_weight)
            weights_snapshot[name] = weight
            if collection_method is not None and not factor.applies_to(collection_method):
                skipped_factors.append(name)
            else:
                applicable.append((name, factor, weight))

        # Re-normalise weights only when factors were skipped
        needs_normalisation = len(skipped_factors) > 0
        total_raw_weight = sum(w for _, _, w in applicable) if needs_normalisation else 1.0
        if total_raw_weight == 0:
            total_raw_weight = 1.0

        factor_results: list[FactorResult] = []
        total_weighted = 0.0

        for name, factor, raw_weight in applicable:
            normalised_weight = raw_weight / total_raw_weight if needs_normalisation else raw_weight
            raw_score = factor.calculate(customer_data, collection_data)
            weighted_score = raw_score * normalised_weight
            # Call `trigger` BEFORE `explain` so a factor can tell the
            # engine which specific policy rule fired, and `explain` can
            # short-circuit to a rule-named message. Default on BaseFactor
            # returns None, so factors that don't gate on named rules
            # take no new behaviour.
            trigger = factor.trigger(customer_data, collection_data)
            explanation = factor.explain(raw_score, trigger=trigger)

            factor_results.append(
                FactorResult(
                    factor_name=name,
                    raw_score=round(raw_score, 4),
                    weight=round(normalised_weight, 4),
                    weighted_score=round(weighted_score, 4),
                    explanation=explanation,
                    trigger=trigger,
                )
            )
            total_weighted += weighted_score

        # Clamp final score to 0-1
        final_score = max(0.0, min(1.0, total_weighted))

        # Map to risk level (score is 0-1, risk thresholds at 0.3 and 0.6)
        risk_level = self._map_risk_level(final_score)
        recommended_action = self._recommend_action(risk_level)
        model_version = (
            self._model_version_for_method(collection_method)
            if collection_method is not None
            else self._model_version(factor_set)
        )

        elapsed_ms = (time.perf_counter_ns() - start) // 1_000_000

        return ScoringResult(
            score=round(final_score, 4),
            risk_level=risk_level,
            recommended_action=recommended_action,
            factors=factor_results,
            skipped_factors=skipped_factors,
            model_version=model_version,
            scoring_duration_ms=max(1, elapsed_ms),
            weights_snapshot={k: round(v, 4) for k, v in weights_snapshot.items()},
        )

    def _map_risk_level(self, score: float) -> str:
        if score <= 0.30:
            return "LOW"
        if score <= 0.60:
            return "MEDIUM"
        return "HIGH"

    def _recommend_action(self, risk_level: str) -> str:
        actions = {
            "LOW": "collect_normally",
            "MEDIUM": "pre_collection_sms",
            "HIGH": "flag_for_review",
        }
        return actions.get(risk_level, "collect_normally")

    def _model_version(self, factor_set: str) -> str:
        """DEPRECATED: kept for the fallback path in legacy callers."""
        versions = {
            "CARD_DEBIT": "heuristic_card_v1",
            "MOBILE_WALLET": "heuristic_wallet_v1",
            "PAYROLL": "heuristic_payroll_v1",
        }
        return versions.get(factor_set, f"heuristic_{factor_set.lower()}_v1")

    def _model_version_for_method(self, method: CollectionMethod) -> str:
        versions = {
            CollectionMethod.CARD: "heuristic_card_v1",
            CollectionMethod.DEBIT_ORDER: "heuristic_card_v1",
            CollectionMethod.MOBILE_MONEY: "heuristic_wallet_v1",
            CollectionMethod.PAYROLL: "heuristic_payroll_v1",
        }
        return versions.get(method, f"heuristic_{method.value.lower()}_v1")

    # Statuses that short-circuit PAYROLL scoring to HIGH. Compared
    # case-insensitively against `customer_data["employment_status"]`.
    _PAYROLL_HARD_FAIL_STATUSES = {"terminated", "dismissed"}

    def _employment_status_override(
        self,
        *,
        customer_data: dict,
        factors: dict,
        custom_weights: dict[str, float] | None,
        start_ns: int,
    ) -> ScoringResult | None:
        """Return a hard-HIGH ScoringResult when the borrower is
        terminated/dismissed; return None otherwise so the normal
        factor loop runs.

        The result carries a single synthetic `employment_status` factor
        row at score 1.0 so the dashboard can render ONE clear reason
        (with a trigger badge) rather than a stack of dampened factor
        contributions. Every real factor in the bundle moves to
        `skipped_factors` so the officer knows nothing else was scored.
        """
        raw_status = customer_data.get("employment_status")
        if not raw_status:
            return None
        status = str(raw_status).strip().lower()
        if status not in self._PAYROLL_HARD_FAIL_STATUSES:
            return None

        trigger = (
            "employment_terminated" if status == "terminated" else "employment_dismissed"
        )
        explanation = (
            "Borrower terminated; payroll deduction cannot succeed"
            if status == "terminated"
            else "Borrower dismissed; payroll deduction cannot succeed"
        )

        # Snapshot the pre-normalisation weights the same way the
        # normal path does, so audit / reproducibility stays complete
        # even on short-circuit paths.
        weights_snapshot: dict[str, float] = {}
        for name, (_, default_weight) in factors.items():
            weight = (custom_weights or {}).get(name, default_weight)
            weights_snapshot[name] = weight

        synthetic = FactorResult(
            factor_name="employment_status",
            raw_score=1.0,
            weight=1.0,
            weighted_score=1.0,
            explanation=explanation,
            trigger=trigger,
        )

        elapsed_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
        return ScoringResult(
            score=1.0,
            risk_level="HIGH",
            recommended_action=self._recommend_action("HIGH"),
            factors=[synthetic],
            skipped_factors=list(factors.keys()),
            model_version=self._model_version_for_method(CollectionMethod.PAYROLL),
            scoring_duration_ms=max(1, elapsed_ms),
            weights_snapshot={k: round(v, 4) for k, v in weights_snapshot.items()},
        )
