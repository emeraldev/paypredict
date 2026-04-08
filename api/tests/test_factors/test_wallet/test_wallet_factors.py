"""Tests for mobile wallet factors: WalletBalanceTrend, TimeSinceLastInflow,
SalaryCycleAlignment, TransactionVelocity, AirtimePurchasePattern."""

from datetime import date

from app.scoring.factors.wallet.wallet_balance_trend import WalletBalanceTrend
from app.scoring.factors.wallet.time_since_inflow import TimeSinceLastInflow
from app.scoring.factors.wallet.salary_cycle import SalaryCycleAlignment
from app.scoring.factors.wallet.transaction_velocity import TransactionVelocity
from app.scoring.factors.wallet.airtime_pattern import AirtimePurchasePattern


# --- WalletBalanceTrend ---

class TestWalletBalanceTrend:
    factor = WalletBalanceTrend()

    def test_stable_balance(self):
        score = self.factor.calculate(
            {"wallet_balance_7d_avg": 500, "wallet_balance_current": 480},
            {"collection_amount": 200},
        )
        assert score == 0.1

    def test_crashed_balance(self):
        score = self.factor.calculate(
            {"wallet_balance_7d_avg": 500, "wallet_balance_current": 100},
            {"collection_amount": 200},
        )
        assert score == 1.0  # 0.9 + 0.3 (can't cover), clamped to 1.0

    def test_cant_cover_collection(self):
        score = self.factor.calculate(
            {"wallet_balance_7d_avg": 500, "wallet_balance_current": 480},
            {"collection_amount": 600},
        )
        assert score == 0.4  # 0.1 + 0.3

    def test_no_data(self):
        assert self.factor.calculate({}, {}) == 0.5

    def test_zero_avg(self):
        score = self.factor.calculate(
            {"wallet_balance_7d_avg": 0, "wallet_balance_current": 100}, {}
        )
        assert score == 0.5


# --- TimeSinceLastInflow ---

class TestTimeSinceLastInflow:
    factor = TimeSinceLastInflow()

    def test_very_recent(self):
        assert self.factor.calculate({"hours_since_last_inflow": 3}, {}) == 0.1

    def test_one_day(self):
        assert self.factor.calculate({"hours_since_last_inflow": 18}, {}) == 0.2

    def test_two_days(self):
        assert self.factor.calculate({"hours_since_last_inflow": 36}, {}) == 0.4

    def test_three_days(self):
        assert self.factor.calculate({"hours_since_last_inflow": 60}, {}) == 0.6

    def test_very_old(self):
        assert self.factor.calculate({"hours_since_last_inflow": 120}, {}) == 0.8

    def test_no_data(self):
        assert self.factor.calculate({}, {}) == 0.5


# --- SalaryCycleAlignment ---

class TestSalaryCycleAlignment:
    factor = SalaryCycleAlignment()

    def test_aligned(self):
        score = self.factor.calculate(
            {"regular_inflow_day": "friday"},
            {"collection_due_date": date(2026, 4, 11)},  # Saturday
        )
        assert score == 0.1

    def test_misaligned(self):
        score = self.factor.calculate(
            {"regular_inflow_day": "friday"},
            {"collection_due_date": date(2026, 4, 16)},  # Thursday
        )
        assert score == 0.75

    def test_no_inflow_day(self):
        score = self.factor.calculate({}, {"collection_due_date": date(2026, 4, 14)})
        assert score == 0.4


# --- TransactionVelocity ---

class TestTransactionVelocity:
    factor = TransactionVelocity()

    def test_normal_activity(self):
        score = self.factor.calculate(
            {"transactions_last_7d": 14, "transactions_avg_7d": 15}, {}
        )
        assert score == 0.1

    def test_slowdown(self):
        score = self.factor.calculate(
            {"transactions_last_7d": 8, "transactions_avg_7d": 15}, {}
        )
        assert score == 0.4

    def test_significant_drop(self):
        score = self.factor.calculate(
            {"transactions_last_7d": 3, "transactions_avg_7d": 15}, {}
        )
        assert score == 0.7

    def test_inactive(self):
        score = self.factor.calculate(
            {"transactions_last_7d": 1, "transactions_avg_7d": 15}, {}
        )
        assert score == 0.9

    def test_no_data(self):
        assert self.factor.calculate({}, {}) == 0.3


# --- AirtimePurchasePattern ---

class TestAirtimePurchasePattern:
    factor = AirtimePurchasePattern()

    def test_recent(self):
        assert self.factor.calculate({"last_airtime_purchase_days_ago": 1}, {}) == 0.1

    def test_week_ago(self):
        assert self.factor.calculate({"last_airtime_purchase_days_ago": 5}, {}) == 0.2

    def test_two_weeks(self):
        assert self.factor.calculate({"last_airtime_purchase_days_ago": 10}, {}) == 0.4

    def test_month_ago(self):
        assert self.factor.calculate({"last_airtime_purchase_days_ago": 25}, {}) == 0.6

    def test_very_old(self):
        assert self.factor.calculate({"last_airtime_purchase_days_ago": 45}, {}) == 0.8

    def test_no_data(self):
        assert self.factor.calculate({}, {}) == 0.3
