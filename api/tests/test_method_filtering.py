"""Tests for collection method filtering and weight re-normalisation."""

from datetime import date

from app.models.score_request import CollectionMethod
from app.scoring.engine import ScoringEngine
from app.scoring.factors.card.card_health import CardHealth
from app.scoring.factors.card.card_type import CardType
from app.scoring.factors.card.debit_order_returns import DebitOrderReturnHistory
from app.scoring.factors.card.day_of_month import DayOfMonthVsPayday
from app.scoring.factors.shared.historical_failure import HistoricalFailureRate
from app.scoring.factors.wallet.wallet_balance_trend import WalletBalanceTrend

engine = ScoringEngine()


class TestAppliesTo:
    """Test the applies_to method on individual factors."""

    def test_card_health_applies_to_card(self):
        assert CardHealth().applies_to(CollectionMethod.CARD) is True

    def test_card_health_not_debit_order(self):
        assert CardHealth().applies_to(CollectionMethod.DEBIT_ORDER) is False

    def test_card_health_not_mobile_money(self):
        assert CardHealth().applies_to(CollectionMethod.MOBILE_MONEY) is False

    def test_card_type_applies_to_card(self):
        assert CardType().applies_to(CollectionMethod.CARD) is True

    def test_card_type_not_debit_order(self):
        assert CardType().applies_to(CollectionMethod.DEBIT_ORDER) is False

    def test_debit_order_returns_applies_to_debit_order(self):
        assert DebitOrderReturnHistory().applies_to(CollectionMethod.DEBIT_ORDER) is True

    def test_debit_order_returns_not_card(self):
        assert DebitOrderReturnHistory().applies_to(CollectionMethod.CARD) is False

    def test_shared_factor_applies_to_all(self):
        f = HistoricalFailureRate()
        assert f.applies_to(CollectionMethod.CARD) is True
        assert f.applies_to(CollectionMethod.DEBIT_ORDER) is True
        assert f.applies_to(CollectionMethod.MOBILE_MONEY) is True

    def test_day_of_month_applies_to_all_card_debit(self):
        f = DayOfMonthVsPayday()
        assert f.applies_to(CollectionMethod.CARD) is True
        assert f.applies_to(CollectionMethod.DEBIT_ORDER) is True

    def test_wallet_factor_applies_to_mobile_money(self):
        f = WalletBalanceTrend()
        assert f.applies_to(CollectionMethod.MOBILE_MONEY) is True
        assert f.applies_to(CollectionMethod.CARD) is False


class TestEngineCardFiltering:
    """Test engine filters correctly for CARD vs DEBIT_ORDER."""

    def test_card_collection_skips_debit_order_returns(self, sa_customer_data, sa_collection_data):
        result = engine.score(
            "CARD_DEBIT", sa_customer_data, sa_collection_data,
            collection_method=CollectionMethod.CARD,
        )
        factor_names = {f.factor_name for f in result.factors}
        assert "card_health" in factor_names
        assert "card_type" in factor_names
        assert "debit_order_return_history" not in factor_names
        assert "debit_order_return_history" in result.skipped_factors

    def test_debit_order_collection_skips_card_factors(self, sa_customer_data):
        collection_data = {
            "collection_amount": 1500.00,
            "collection_due_date": date(2026, 4, 15),
            "collection_method": "DEBIT_ORDER",
        }
        result = engine.score(
            "CARD_DEBIT", sa_customer_data, collection_data,
            collection_method=CollectionMethod.DEBIT_ORDER,
        )
        factor_names = {f.factor_name for f in result.factors}
        assert "debit_order_return_history" in factor_names
        assert "card_health" not in factor_names
        assert "card_type" not in factor_names
        assert "card_health" in result.skipped_factors
        assert "card_type" in result.skipped_factors

    def test_card_collection_has_fewer_factors(self, sa_customer_data, sa_collection_data):
        result = engine.score(
            "CARD_DEBIT", sa_customer_data, sa_collection_data,
            collection_method=CollectionMethod.CARD,
        )
        # 8 total - 1 skipped (debit_order_return_history) = 7 evaluated
        assert len(result.factors) == 7
        assert len(result.skipped_factors) == 1

    def test_debit_order_collection_has_fewer_factors(self, sa_customer_data):
        collection_data = {
            "collection_amount": 1500.00,
            "collection_due_date": date(2026, 4, 15),
        }
        result = engine.score(
            "CARD_DEBIT", sa_customer_data, collection_data,
            collection_method=CollectionMethod.DEBIT_ORDER,
        )
        # 8 total - 2 skipped (card_health, card_type) = 6 evaluated
        assert len(result.factors) == 6
        assert len(result.skipped_factors) == 2


class TestWeightNormalisation:
    """Test that weights are re-normalised when factors are skipped."""

    def test_card_weights_sum_to_one(self, sa_customer_data, sa_collection_data):
        result = engine.score(
            "CARD_DEBIT", sa_customer_data, sa_collection_data,
            collection_method=CollectionMethod.CARD,
        )
        total_weight = sum(f.weight for f in result.factors)
        assert abs(total_weight - 1.0) < 0.01

    def test_debit_order_weights_sum_to_one(self, sa_customer_data):
        collection_data = {
            "collection_amount": 1500.00,
            "collection_due_date": date(2026, 4, 15),
        }
        result = engine.score(
            "CARD_DEBIT", sa_customer_data, collection_data,
            collection_method=CollectionMethod.DEBIT_ORDER,
        )
        total_weight = sum(f.weight for f in result.factors)
        assert abs(total_weight - 1.0) < 0.01

    def test_no_method_runs_all_factors(self, sa_customer_data, sa_collection_data):
        result = engine.score("CARD_DEBIT", sa_customer_data, sa_collection_data)
        assert len(result.factors) == 8
        assert len(result.skipped_factors) == 0

    def test_card_vs_debit_order_different_scores(self, sa_customer_data):
        """Same customer, different collection method = different score."""
        collection_data = {
            "collection_amount": 1500.00,
            "collection_due_date": date(2026, 4, 15),
        }
        card_result = engine.score(
            "CARD_DEBIT", sa_customer_data, collection_data,
            collection_method=CollectionMethod.CARD,
        )
        debit_result = engine.score(
            "CARD_DEBIT", sa_customer_data, collection_data,
            collection_method=CollectionMethod.DEBIT_ORDER,
        )
        # Scores should differ because different factors run
        assert card_result.score != debit_result.score
        assert set(card_result.skipped_factors) != set(debit_result.skipped_factors)


class TestWalletFiltering:
    """Test that wallet factors only run for MOBILE_MONEY."""

    def test_mobile_money_runs_all_wallet_factors(self, zm_customer_data, zm_collection_data):
        result = engine.score(
            "MOBILE_WALLET", zm_customer_data, zm_collection_data,
            collection_method=CollectionMethod.MOBILE_MONEY,
        )
        assert len(result.factors) == 8
        assert len(result.skipped_factors) == 0

    def test_wallet_weights_sum_to_one(self, zm_customer_data, zm_collection_data):
        result = engine.score(
            "MOBILE_WALLET", zm_customer_data, zm_collection_data,
            collection_method=CollectionMethod.MOBILE_MONEY,
        )
        total_weight = sum(f.weight for f in result.factors)
        assert abs(total_weight - 1.0) < 0.01
