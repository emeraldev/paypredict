from app.models.score_request import CollectionMethod
from app.scoring.factors.base import BaseFactor


class ThresholdHeadroom(BaseFactor):
    """The dominant payroll factor. Scores against two gates:

    1. **Ceiling** (regulatory): total payroll deductions must stay
       under `deduction_threshold_pct` of gross salary (40% is the
       Zambia default). If existing deductions push the borrower
       near that cap the lender's deduction gets rejected.
    2. **Floor** (business policy): take-home pay after this
       collection must stay above `min_take_home_pct` of gross salary
       (0.30 is the common Zambian floor). Below the floor the
       lender declines the loan to protect the borrower from
       over-indebtedness, regardless of whether the ceiling allows it.

    When both gates are supplied the factor returns the worse of the
    two scores. When the floor field is omitted or None, the floor
    check is skipped and behaviour is identical to the ceiling-only
    original. `trigger()` emits a short code when a specific gate
    is BREACHED (not just tight) so the dashboard can surface a
    precise reason.

    Data (all optional, all in `customer_data`):
      - gross_salary: Decimal
      - current_total_deductions: Decimal — everyone else's deductions
      - deduction_threshold_pct: float, defaults to 0.40
      - min_take_home_pct: float | None — business-policy floor

    Compared against `collection_data.collection_amount`.
    """

    applicable_methods = [CollectionMethod.PAYROLL]

    # Buffer-tightness thresholds reused by both gates so the factor
    # emits consistent scores for comparable degrees of pressure.
    _TIGHT_BAND = (0.05, 0.15, 0.30)

    def calculate(self, customer_data: dict, collection_data: dict) -> float:
        gross_salary = customer_data.get("gross_salary")
        current_deductions = customer_data.get("current_total_deductions")
        # Pydantic serialises optional fields as explicit None when omitted,
        # so .get(key, default) doesn't shield us — handle None first, same
        # trap as LoanCyclingBehaviour hit.
        threshold_pct = customer_data.get("deduction_threshold_pct")
        if threshold_pct is None:
            threshold_pct = 0.40  # Zambia default
        min_take_home_pct = customer_data.get("min_take_home_pct")
        collection_amount = collection_data.get("collection_amount", 0)

        if not gross_salary:
            return 0.5  # No salary data — insufficient info to judge

        gross_f = float(gross_salary)
        amount = float(collection_amount)

        ceiling_score = self._ceiling_score(
            gross=gross_f,
            current_deductions=current_deductions,
            threshold_pct=float(threshold_pct),
            amount=amount,
        )

        if min_take_home_pct is None:
            return ceiling_score

        floor_score = self._floor_score(
            gross=gross_f,
            current_deductions=current_deductions,
            min_take_home_pct=float(min_take_home_pct),
            amount=amount,
        )
        return max(ceiling_score, floor_score)

    def _ceiling_score(
        self,
        *,
        gross: float,
        current_deductions,
        threshold_pct: float,
        amount: float,
    ) -> float:
        """Original ceiling logic, extracted so the floor can mirror its shape."""
        max_deductions = gross * threshold_pct

        if current_deductions is not None:
            headroom = max_deductions - float(current_deductions)
            if headroom <= 0:
                return 1.0  # Already at/over the ceiling — deduction will fail
            if amount > headroom:
                return 0.9  # Our deduction alone exceeds available headroom
            buffer_ratio = (headroom - amount) / max_deductions
            return self._bucket_tightness(buffer_ratio)

        if max_deductions <= 0:
            return 0.5
        ratio = amount / max_deductions
        if ratio > 0.8:
            return 0.8
        if ratio > 0.5:
            return 0.5
        if ratio > 0.3:
            return 0.3
        return 0.1

    def _floor_score(
        self,
        *,
        gross: float,
        current_deductions,
        min_take_home_pct: float,
        amount: float,
    ) -> float:
        """Score against the net-pay floor.

        If `current_total_deductions` is missing, treat it as 0 — a
        weaker check (the loan amount alone counts against the floor)
        but still meaningful. The resulting floor score never exceeds
        what a fully-informed check would produce because the missing
        term can only make the computed take-home LOOK better than it
        really is.
        """
        current = float(current_deductions) if current_deductions is not None else 0.0
        post_net_pay = gross - current - amount
        post_net_pay_pct = post_net_pay / gross

        if post_net_pay_pct < 0:
            return 1.0  # Deduction would leave the borrower owing money
        if post_net_pay_pct < min_take_home_pct:
            return 0.9  # Floor broken

        # Buffer above the floor, scaled to [0, 1] so tightness buckets
        # fire at comparable positions to the ceiling gate.
        headroom_pct = post_net_pay_pct - min_take_home_pct
        max_headroom_pct = 1.0 - min_take_home_pct
        if max_headroom_pct <= 0:
            return 0.1
        buffer_ratio = headroom_pct / max_headroom_pct
        return self._bucket_tightness(buffer_ratio)

    def _bucket_tightness(self, buffer_ratio: float) -> float:
        """Shared tightness buckets so ceiling and floor score comparably."""
        low, mid, high = self._TIGHT_BAND
        if buffer_ratio < low:
            return 0.8
        if buffer_ratio < mid:
            return 0.5
        if buffer_ratio < high:
            return 0.3
        return 0.1

    def trigger(self, customer_data: dict, collection_data: dict) -> str | None:
        """Emit "floor_breach" / "ceiling_breach" when a named rule fires.

        Tight-but-not-breached scores do NOT emit a trigger — the
        bucketed explain string already reads correctly in that case,
        and promoting every tight buffer to a trigger would make the
        dashboard badge noisy. Priority on tie: floor_breach wins
        because it is the harder lender-side decision (compliance
        failure vs business-policy failure both land the deduction in
        the same place, but the floor failure is also the one that
        tells the lender to decline on affordability grounds).
        """
        gross_salary = customer_data.get("gross_salary")
        if not gross_salary:
            return None
        gross = float(gross_salary)
        amount = float(collection_data.get("collection_amount", 0))
        current_raw = customer_data.get("current_total_deductions")

        min_take_home_pct = customer_data.get("min_take_home_pct")
        if min_take_home_pct is not None:
            current = float(current_raw) if current_raw is not None else 0.0
            post_net_pay_pct = (gross - current - amount) / gross
            if post_net_pay_pct < float(min_take_home_pct):
                return "floor_breach"

        threshold_pct = customer_data.get("deduction_threshold_pct")
        if threshold_pct is None:
            threshold_pct = 0.40
        if current_raw is not None:
            headroom = gross * float(threshold_pct) - float(current_raw)
            if headroom <= 0:
                return "ceiling_breach"

        return None

    def explain(self, score: float, trigger: str | None = None) -> str:
        if trigger == "floor_breach":
            return "Would reduce take-home pay below the minimum take-home floor"
        if trigger == "ceiling_breach":
            return "Borrower already at or over the deduction ceiling — deduction will be rejected"
        if score >= 0.95:
            return "Borrower already at or over the deduction ceiling — deduction will be rejected"
        if score >= 0.85:
            return "Deduction alone exceeds available salary threshold headroom"
        if score >= 0.7:
            return "Very tight salary threshold headroom — high rejection risk"
        if score >= 0.4:
            return "Moderate salary threshold headroom"
        if score > 0.15:
            return "Comfortable salary threshold headroom"
        return "Plenty of threshold headroom — low rejection risk"
