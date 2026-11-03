"""Tests for PAYROLL factor set: ThresholdHeadroom, DeductionToIncomeRatio,
ResubmissionHistory, BorrowerSegment.

Mirrors the structure of tests/test_factors/test_shared/test_shared_factors.py
— one class per factor, class-level `factor = FactorClass()` attribute.
"""

from app.models.score_request import CollectionMethod
from app.scoring.factors.payroll.borrower_segment import BorrowerSegment
from app.scoring.factors.payroll.deduction_to_income import DeductionToIncomeRatio
from app.scoring.factors.payroll.resubmission_history import ResubmissionHistory
from app.scoring.factors.payroll.threshold_headroom import ThresholdHeadroom


# --- ThresholdHeadroom ---

class TestThresholdHeadroom:
    factor = ThresholdHeadroom()

    def test_no_salary_data_returns_moderate_default(self):
        assert self.factor.calculate({}, {"collection_amount": 1000}) == 0.5

    def test_over_threshold_returns_worst(self):
        # Current deductions already exceed the 40% cap.
        score = self.factor.calculate(
            {"gross_salary": 10000, "current_total_deductions": 5000},
            {"collection_amount": 500},
        )
        assert score == 1.0

    def test_deduction_exceeds_available_headroom(self):
        # Cap = 4000, existing = 3600, headroom = 400, our deduction = 800.
        score = self.factor.calculate(
            {"gross_salary": 10000, "current_total_deductions": 3600},
            {"collection_amount": 800},
        )
        assert score == 0.9

    def test_very_tight_buffer_after_deduction(self):
        # Cap = 4000, existing = 3400, headroom = 600, our deduction = 500.
        # Post-deduction buffer = 100 → 100 / 4000 = 2.5% → < 5% branch.
        score = self.factor.calculate(
            {"gross_salary": 10000, "current_total_deductions": 3400},
            {"collection_amount": 500},
        )
        assert score == 0.8

    def test_comfortable_headroom(self):
        # Cap = 4000, existing = 1000, headroom = 3000, our deduction = 500.
        # Post-deduction buffer = 2500 → 62.5% → returns 0.1.
        score = self.factor.calculate(
            {"gross_salary": 10000, "current_total_deductions": 1000},
            {"collection_amount": 500},
        )
        assert score == 0.1

    def test_only_gross_salary_ratio_fallback(self):
        # Cap = 4000, deduction 3600 → ratio 0.9 → > 0.8 branch → 0.8.
        score = self.factor.calculate(
            {"gross_salary": 10000},
            {"collection_amount": 3600},
        )
        assert score == 0.8

    def test_custom_threshold_percentage(self):
        # Zambia default is 0.40 but the factor respects any override.
        # Cap = 10000 * 0.30 = 3000, existing = 2400, headroom = 600,
        # our deduction = 700 → exceeds → 0.9.
        score = self.factor.calculate(
            {
                "gross_salary": 10000,
                "current_total_deductions": 2400,
                "deduction_threshold_pct": 0.30,
            },
            {"collection_amount": 700},
        )
        assert score == 0.9

    def test_applicable_methods_is_payroll_only(self):
        assert self.factor.applicable_methods == [CollectionMethod.PAYROLL]
        assert self.factor.applies_to(CollectionMethod.PAYROLL)
        assert not self.factor.applies_to(CollectionMethod.CARD)

    def test_none_threshold_pct_falls_back_to_zambia_default(self):
        """Regression: Pydantic emits explicit None for omitted optional
        fields — .get(key, default) doesn't fire the default, so we have to
        handle None explicitly. Bug hit in the bulk endpoint when a caller
        omitted `deduction_threshold_pct`, TypeError from float(None)."""
        score = self.factor.calculate(
            {
                "gross_salary": 10000,
                "current_total_deductions": 1200,
                "deduction_threshold_pct": None,  # explicit None, not omitted
            },
            {"collection_amount": 800},
        )
        # Should behave the same as the "loose headroom" case with 40% default
        # applied: cap = 4000, headroom = 2800, buffer after 800 = 2000 → 50%
        # → 0.1 branch.
        assert score == 0.1

    def test_omitted_threshold_pct_falls_back_to_zambia_default(self):
        """When the key isn't in the dict at all — same expected behaviour."""
        score = self.factor.calculate(
            {"gross_salary": 10000, "current_total_deductions": 1200},
            {"collection_amount": 800},
        )
        assert score == 0.1

    # ---- 30% take-home floor gate (Kalene pilot asks for both gates) ----

    def test_floor_absent_is_ceiling_only(self):
        """Baseline: omitting `min_take_home_pct` must leave scores
        identical to the ceiling-only behaviour above. Backwards
        compatibility for every current caller."""
        score = self.factor.calculate(
            {"gross_salary": 10000, "current_total_deductions": 1200},
            {"collection_amount": 800},
        )
        assert score == 0.1
        assert (
            self.factor.trigger(
                {"gross_salary": 10000, "current_total_deductions": 1200},
                {"collection_amount": 800},
            )
            is None
        )

    def test_floor_passes_with_ceiling(self):
        # Gross 10000, current 1000, amount 500 -> net 8500 -> 85% take-home.
        # Floor is 30%, far above. Ceiling buffer is also loose -> low score.
        customer = {
            "gross_salary": 10000,
            "current_total_deductions": 1000,
            "min_take_home_pct": 0.30,
        }
        collection = {"collection_amount": 500}
        assert self.factor.calculate(customer, collection) == 0.1
        assert self.factor.trigger(customer, collection) is None

    def test_floor_breach_dominates_passing_ceiling(self):
        # Gross 10000, current 6500, amount 1000 -> net 2500 -> 25% take-home.
        # Floor 30% is BREACHED (25 < 30). Ceiling: cap=4000, existing=6500 is
        # already over -> ceiling_score is 1.0, not 0.9. Pick a mix that keeps
        # ceiling PASSING: gross 10000, current 3000, amount 400 -> cap=4000,
        # headroom=1000 (loose) -> ceiling 0.1. Net = 10000-3000-400 = 6600 ->
        # 66% take-home, FAR above the floor. Not a floor breach.
        # Build a floor-only breach: gross=10000, current=0 (no other
        # deductions), amount=7500 -> net=2500 -> 25% -> floor BREACH.
        # Ceiling: cap=4000, headroom=4000, amount 7500 > headroom -> ceiling
        # also fires 0.9. So the "floor broken but ceiling passes" case is
        # vanishingly rare in practice; it needs ceiling_threshold > 1 - floor,
        # i.e. threshold 0.75 and floor 0.30.
        customer = {
            "gross_salary": 10000,
            "current_total_deductions": 0,
            "deduction_threshold_pct": 0.75,  # relaxed ceiling for test isolation
            "min_take_home_pct": 0.30,
        }
        collection = {"collection_amount": 7500}
        # Net = 10000 - 0 - 7500 = 2500 -> 25% -> floor BREACH -> 0.9.
        # Ceiling: cap=7500, headroom=7500, amount=7500 -> headroom - amount = 0
        # buffer_ratio = 0/7500 = 0 -> < 0.05 band -> 0.8.
        assert self.factor.calculate(customer, collection) == 0.9
        assert self.factor.trigger(customer, collection) == "floor_breach"

    def test_ceiling_breach_dominates_passing_floor(self):
        # Current deductions already exceed the 40% ceiling. Floor is loose.
        customer = {
            "gross_salary": 10000,
            "current_total_deductions": 5000,  # 50% > 40% cap
            "min_take_home_pct": 0.10,  # very loose floor
        }
        collection = {"collection_amount": 100}
        # Ceiling: headroom = 4000-5000 = -1000 -> 1.0. Floor: net = 4900 -> 49%
        # -> far above 10% floor -> buffer_ratio ~0.43 -> 0.1. max -> 1.0.
        assert self.factor.calculate(customer, collection) == 1.0
        assert self.factor.trigger(customer, collection) == "ceiling_breach"

    def test_both_breached_scores_worst(self):
        # Ceiling: current 5000 on cap 4000 -> breach, 1.0.
        # Floor: net = 10000 - 5000 - 500 = 4500 -> 45% -> above 30% -> no
        # floor breach. So this isn't actually both-breached — construct one.
        # Need: current + amount > gross * (1 - min_take_home_pct) AND current
        # > gross * threshold_pct. With defaults 0.40/0.30: current > 4000 AND
        # current + amount > 7000. Current=5000, amount=2500 -> both fire.
        customer = {
            "gross_salary": 10000,
            "current_total_deductions": 5000,
            "min_take_home_pct": 0.30,
        }
        collection = {"collection_amount": 2500}
        # Ceiling breach -> 1.0. Floor: net = 2500 -> 25% -> breach -> 0.9.
        # max(1.0, 0.9) = 1.0. Trigger: floor_breach has priority per factor
        # (lender-side the floor is the harder decision).
        assert self.factor.calculate(customer, collection) == 1.0
        assert self.factor.trigger(customer, collection) == "floor_breach"

    def test_floor_with_none_current_deductions_treats_as_zero(self):
        # Weak but valid check: when current_total_deductions is missing,
        # the floor applies with current treated as 0. Amount alone must
        # keep take-home above the floor.
        customer = {
            "gross_salary": 10000,
            "min_take_home_pct": 0.30,
        }
        # Amount 8000 -> net = 10000 - 0 - 8000 = 2000 -> 20% -> floor breach.
        collection = {"collection_amount": 8000}
        # Ceiling fallback: only gross known -> ratio = 8000 / 4000 = 2 -> 0.8
        # Floor breach: 0.9. max = 0.9.
        assert self.factor.calculate(customer, collection) == 0.9
        assert self.factor.trigger(customer, collection) == "floor_breach"

    def test_explain_uses_breach_message_when_trigger_present(self):
        # No trigger: existing bucketed message applies.
        assert self.factor.explain(0.1).startswith("Plenty of threshold headroom")
        # Floor breach: dedicated message.
        assert (
            self.factor.explain(0.9, trigger="floor_breach")
            == "Would reduce take-home pay below the minimum take-home floor"
        )
        # Ceiling breach: same existing message as the score >= 0.95 bucket.
        assert "deduction ceiling" in self.factor.explain(
            0.9, trigger="ceiling_breach"
        )


# --- DeductionToIncomeRatio ---

class TestDeductionToIncomeRatio:
    factor = DeductionToIncomeRatio()

    def test_no_income_returns_moderate_default(self):
        assert self.factor.calculate({}, {"collection_amount": 1000}) == 0.5

    def test_zero_income_returns_moderate_default(self):
        # Guards against division by zero.
        assert self.factor.calculate({"net_pay": 0}, {"collection_amount": 500}) == 0.5

    def test_deduction_over_half_of_income_is_very_high(self):
        assert (
            self.factor.calculate({"net_pay": 5000}, {"collection_amount": 2600}) == 0.9
        )

    def test_small_deduction_relative_to_income(self):
        assert (
            self.factor.calculate({"net_pay": 10000}, {"collection_amount": 500}) == 0.1
        )

    def test_prefers_net_pay_over_gross(self):
        # 500 / 5000 = 10% (low). If gross were used, 500 / 20000 = 2.5%,
        # still low but branches would differ — just prove net_pay wins.
        assert self.factor.calculate(
            {"net_pay": 5000, "gross_salary": 20000},
            {"collection_amount": 500},
        ) == 0.1  # 10% → still small


# --- ResubmissionHistory ---

class TestResubmissionHistory:
    factor = ResubmissionHistory()

    def test_no_data_mild_default(self):
        assert self.factor.calculate({}, {}) == 0.3

    def test_zero_resubmissions_clean(self):
        assert self.factor.calculate({"resubmission_count": 0}, {}) == 0.0

    def test_one_resubmission_one_off(self):
        assert self.factor.calculate({"resubmission_count": 1}, {}) == 0.3

    def test_three_or_more_persistent(self):
        assert self.factor.calculate({"resubmission_count": 3}, {}) == 0.85
        assert self.factor.calculate({"resubmission_count": 10}, {}) == 0.85


# --- BorrowerSegment ---

class TestBorrowerSegment:
    factor = BorrowerSegment()

    def test_unknown_segment_moderate_default(self):
        assert self.factor.calculate({}, {}) == 0.4
        # Unrecognised label
        assert self.factor.calculate({"borrower_segment": "astronaut"}, {}) == 0.4

    def test_government_is_lowest_risk(self):
        assert self.factor.calculate({"borrower_segment": "government"}, {}) == 0.2

    def test_mining_is_higher_than_government(self):
        gov = self.factor.calculate({"borrower_segment": "government"}, {})
        mining = self.factor.calculate({"borrower_segment": "mining"}, {})
        assert mining > gov

    def test_case_insensitive(self):
        for variant in ("Government", "GOVERNMENT", " government "):
            assert self.factor.calculate({"borrower_segment": variant}, {}) == 0.2
