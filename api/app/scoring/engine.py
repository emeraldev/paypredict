import time
from dataclasses import dataclass, field

from app.models.score_request import CollectionMethod
from app.scoring.registry import get_factors_for_set


@dataclass
class FactorResult:
    factor_name: str
    raw_score: float
    weight: float
    weighted_score: float
    explanation: str


@dataclass
class ScoringResult:
    score: float
    risk_level: str
    recommended_action: str
    factors: list[FactorResult]
    skipped_factors: list[str]
    model_version: str
    scoring_duration_ms: int


class ScoringEngine:
    """Orchestrates factor evaluation and produces a final risk score."""

    def score(
        self,
        factor_set: str,
        customer_data: dict,
        collection_data: dict,
        custom_weights: dict[str, float] | None = None,
        collection_method: CollectionMethod | None = None,
    ) -> ScoringResult:
        start = time.perf_counter_ns()

        factors = get_factors_for_set(factor_set)

        # Separate applicable and skipped factors
        applicable: list[tuple[str, object, float]] = []
        skipped_factors: list[str] = []

        for name, (factor, default_weight) in factors.items():
            weight = (custom_weights or {}).get(name, default_weight)
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
            explanation = factor.explain(raw_score)

            factor_results.append(
                FactorResult(
                    factor_name=name,
                    raw_score=round(raw_score, 4),
                    weight=round(normalised_weight, 4),
                    weighted_score=round(weighted_score, 4),
                    explanation=explanation,
                )
            )
            total_weighted += weighted_score

        # Clamp final score to 0-1
        final_score = max(0.0, min(1.0, total_weighted))

        # Map to risk level (score is 0-1, risk thresholds at 0.3 and 0.6)
        risk_level = self._map_risk_level(final_score)
        recommended_action = self._recommend_action(risk_level)
        model_version = self._model_version(factor_set)

        elapsed_ms = (time.perf_counter_ns() - start) // 1_000_000

        return ScoringResult(
            score=round(final_score, 4),
            risk_level=risk_level,
            recommended_action=recommended_action,
            factors=factor_results,
            skipped_factors=skipped_factors,
            model_version=model_version,
            scoring_duration_ms=max(1, elapsed_ms),
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
        versions = {
            "CARD_DEBIT": "heuristic_card_v1",
            "MOBILE_WALLET": "heuristic_wallet_v1",
        }
        return versions.get(factor_set, f"heuristic_{factor_set.lower()}_v1")
