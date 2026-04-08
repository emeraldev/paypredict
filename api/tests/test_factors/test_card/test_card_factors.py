"""Tests for card/debit order factors: DayOfMonthVsPayday, DaysSinceLastPayment,
OrderValueVsAverage, CardHealth, CardType, DebitOrderReturnHistory."""

from datetime import date, timedelta

from app.scoring.factors.card.day_of_month import DayOfMonthVsPayday
from app.scoring.factors.card.days_since_payment import DaysSinceLastPayment
from app.scoring.factors.card.order_value import OrderValueVsAverage
from app.scoring.factors.card.card_health import CardHealth
from app.scoring.factors.card.card_type import CardType
from app.scoring.factors.card.debit_order_returns import DebitOrderReturnHistory


# --- DayOfMonthVsPayday ---

class TestDayOfMonthVsPayday:
    factor = DayOfMonthVsPayday()

    def test_early_month_no_salary_day(self):
        assert self.factor.calculate({}, {"collection_due_date": date(2026, 4, 3)}) == 0.1

    def test_mid_month_no_salary_day(self):
        assert self.factor.calculate({}, {"collection_due_date": date(2026, 4, 10)}) == 0.3

    def test_late_month_no_salary_day(self):
        assert self.factor.calculate({}, {"collection_due_date": date(2026, 4, 20)}) == 0.5

    def test_end_month_no_salary_day(self):
        assert self.factor.calculate({}, {"collection_due_date": date(2026, 4, 28)}) == 0.8

    def test_with_salary_day_aligned(self):
        score = self.factor.calculate(
            {"known_salary_day": 25}, {"collection_due_date": date(2026, 4, 26)}
        )
        assert score == 0.1

    def test_with_salary_day_misaligned(self):
        score = self.factor.calculate(
            {"known_salary_day": 25}, {"collection_due_date": date(2026, 4, 15)}
        )
        assert score == 0.8

    def test_no_due_date(self):
        assert self.factor.calculate({}, {}) == 0.4


# --- DaysSinceLastPayment ---

class TestDaysSinceLastPayment:
    factor = DaysSinceLastPayment()

    def test_recent_payment(self):
        last = date.today() - timedelta(days=5)
        score = self.factor.calculate({"last_successful_payment_date": last}, {})
        assert 0.0 <= score <= 0.1

    def test_old_payment(self):
        last = date.today() - timedelta(days=120)
        assert self.factor.calculate({"last_successful_payment_date": last}, {}) == 1.0

    def test_no_history(self):
        assert self.factor.calculate({}, {}) == 1.0

    def test_string_date(self):
        last = (date.today() - timedelta(days=45)).isoformat()
        assert self.factor.calculate({"last_successful_payment_date": last}, {}) == 0.5


# --- OrderValueVsAverage ---

class TestOrderValueVsAverage:
    factor = OrderValueVsAverage()

    def test_normal_amount(self):
        score = self.factor.calculate(
            {"average_collection_amount": 1000}, {"collection_amount": 1100}
        )
        assert score == 0.1

    def test_double_amount(self):
        score = self.factor.calculate(
            {"average_collection_amount": 750}, {"collection_amount": 1500}
        )
        assert score == 0.4

    def test_very_high_amount(self):
        score = self.factor.calculate(
            {"average_collection_amount": 500}, {"collection_amount": 2000}
        )
        assert score == 0.8

    def test_no_average(self):
        assert self.factor.calculate({}, {"collection_amount": 1000}) == 0.3


# --- CardHealth ---

class TestCardHealth:
    factor = CardHealth()

    def test_healthy_card(self):
        expiry = date.today() + timedelta(days=365)
        assert self.factor.calculate(
            {"card_expiry_date": expiry, "last_decline_code": None}, {}
        ) == 0.1

    def test_expired_card(self):
        expiry = date.today() - timedelta(days=30)
        assert self.factor.calculate({"card_expiry_date": expiry}, {}) == 1.0

    def test_expiring_soon(self):
        expiry = date.today() + timedelta(days=45)
        assert self.factor.calculate({"card_expiry_date": expiry}, {}) == 0.7

    def test_hard_decline(self):
        expiry = date.today() + timedelta(days=365)
        assert self.factor.calculate(
            {"card_expiry_date": expiry, "last_decline_code": "card_cancelled"}, {}
        ) == 0.4

    def test_soft_decline(self):
        expiry = date.today() + timedelta(days=45)
        score = self.factor.calculate(
            {"card_expiry_date": expiry, "last_decline_code": "insufficient_funds"}, {}
        )
        assert abs(score - 0.8) < 1e-9

    def test_no_card_data(self):
        assert self.factor.calculate({}, {}) == 0.3


# --- CardType ---

class TestCardType:
    factor = CardType()

    def test_credit(self):
        assert self.factor.calculate({"card_type": "credit"}, {}) == 0.2

    def test_debit(self):
        assert self.factor.calculate({"card_type": "debit"}, {}) == 0.5

    def test_unknown(self):
        assert self.factor.calculate({}, {}) == 0.4


# --- DebitOrderReturnHistory ---

class TestDebitOrderReturnHistory:
    factor = DebitOrderReturnHistory()

    def test_no_returns(self):
        assert self.factor.calculate({}, {}) == 0.0

    def test_one_return(self):
        assert self.factor.calculate({"debit_order_returns": ["insufficient_funds"]}, {}) == 0.3

    def test_two_returns(self):
        score = self.factor.calculate(
            {"debit_order_returns": ["insufficient_funds", "general_decline"]}, {}
        )
        assert score == 0.6

    def test_three_returns(self):
        assert self.factor.calculate({"debit_order_returns": ["a", "b", "c"]}, {}) == 0.9

    def test_account_closed(self):
        assert self.factor.calculate({"debit_order_returns": ["account_closed"]}, {}) == 1.0

    def test_disputed_adds(self):
        assert self.factor.calculate({"debit_order_returns": ["disputed"]}, {}) == 0.5
