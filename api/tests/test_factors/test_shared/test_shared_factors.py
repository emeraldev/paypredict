"""Tests for shared factors: HistoricalFailureRate, InstalmentPosition,
ConcurrentLoanCount, LoanCyclingBehaviour."""

from app.scoring.factors.shared.historical_failure import HistoricalFailureRate
from app.scoring.factors.shared.instalment_position import InstalmentPosition
from app.scoring.factors.shared.concurrent_loans import ConcurrentLoanCount
from app.scoring.factors.shared.loan_cycling import LoanCyclingBehaviour


# --- HistoricalFailureRate ---

class TestHistoricalFailureRate:
    factor = HistoricalFailureRate()

    def test_normal_case(self):
        score = self.factor.calculate({"total_payments": 10, "successful_payments": 7}, {})
        assert abs(score - 0.3) < 1e-9

    def test_perfect_history(self):
        assert self.factor.calculate({"total_payments": 20, "successful_payments": 20}, {}) == 0.0

    def test_all_failures(self):
        assert self.factor.calculate({"total_payments": 5, "successful_payments": 0}, {}) == 1.0

    def test_no_history(self):
        assert self.factor.calculate({"total_payments": 0, "successful_payments": 0}, {}) == 0.5

    def test_missing_fields(self):
        assert self.factor.calculate({}, {}) == 0.5

    def test_explain(self):
        assert "30.0%" in self.factor.explain(0.3)


# --- InstalmentPosition ---

class TestInstalmentPosition:
    factor = InstalmentPosition()

    def test_early_instalment(self):
        score = self.factor.calculate(
            {"instalment_number": 1, "total_instalments": 6}, {}
        )
        assert round(score, 3) == round(1 / 6 * 0.8, 3)

    def test_late_instalment(self):
        score = self.factor.calculate(
            {"instalment_number": 5, "total_instalments": 6}, {}
        )
        assert round(score, 3) == round(5 / 6 * 0.8, 3)

    def test_no_data(self):
        assert self.factor.calculate({}, {}) == 0.5


# --- ConcurrentLoanCount ---

class TestConcurrentLoanCount:
    factor = ConcurrentLoanCount()

    def test_no_loans(self):
        assert self.factor.calculate({"active_loan_count": 0}, {}) == 0.0

    def test_one_loan(self):
        assert self.factor.calculate({"active_loan_count": 1}, {}) == 0.2

    def test_two_loans(self):
        assert self.factor.calculate({"active_loan_count": 2}, {}) == 0.5

    def test_many_loans(self):
        assert self.factor.calculate({"active_loan_count": 5}, {}) == 0.8

    def test_no_data(self):
        assert self.factor.calculate({}, {}) == 0.3


# --- LoanCyclingBehaviour ---

class TestLoanCyclingBehaviour:
    factor = LoanCyclingBehaviour()

    def test_cycling_detected(self):
        score = self.factor.calculate(
            {"new_loan_within_repayment_period": True, "loans_taken_last_90d": 1}, {}
        )
        assert score == 0.8

    def test_high_frequency(self):
        score = self.factor.calculate(
            {"new_loan_within_repayment_period": False, "loans_taken_last_90d": 3}, {}
        )
        assert score == 0.6

    def test_moderate_frequency(self):
        score = self.factor.calculate(
            {"new_loan_within_repayment_period": False, "loans_taken_last_90d": 2}, {}
        )
        assert score == 0.3

    def test_normal(self):
        score = self.factor.calculate(
            {"new_loan_within_repayment_period": False, "loans_taken_last_90d": 1}, {}
        )
        assert score == 0.1
