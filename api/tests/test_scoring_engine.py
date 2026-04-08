"""Tests for the ScoringEngine orchestrator."""

from datetime import date

from app.scoring.engine import ScoringEngine

engine = ScoringEngine()


class TestScoringEngineCard:
    def test_scores_all_8_card_factors(self, sa_customer_data, sa_collection_data):
        result = engine.score("CARD_DEBIT", sa_customer_data, sa_collection_data)
        assert len(result.factors) == 8
        assert 0.0 <= result.score <= 1.0
        assert result.risk_level in ("LOW", "MEDIUM", "HIGH")
        assert result.model_version == "heuristic_card_v1"
        assert result.scoring_duration_ms >= 1

    def test_factor_names(self, sa_customer_data, sa_collection_data):
        result = engine.score("CARD_DEBIT", sa_customer_data, sa_collection_data)
        names = {f.factor_name for f in result.factors}
        expected = {
            "historical_failure_rate", "day_of_month_vs_payday",
            "days_since_last_payment", "instalment_position",
            "order_value_vs_average", "card_health",
            "card_type", "debit_order_return_history",
        }
        assert names == expected

    def test_low_risk_customer(self):
        customer = {
            "total_payments": 20,
            "successful_payments": 20,
            "last_successful_payment_date": date.today().isoformat(),
            "average_collection_amount": 1000.00,
            "instalment_number": 1,
            "total_instalments": 6,
            "card_type": "credit",
            "card_expiry_date": "2028-12-31",
        }
        collection = {
            "collection_amount": 1000.00,
            "collection_due_date": date(2026, 4, 2),  # Just after month start
            "collection_method": "CARD",
        }
        result = engine.score("CARD_DEBIT", customer, collection)
        assert result.risk_level == "LOW"
        assert result.recommended_action == "collect_normally"

    def test_high_risk_customer(self):
        customer = {
            "total_payments": 5,
            "successful_payments": 1,
            "card_type": "debit",
            "card_expiry_date": "2025-01-01",  # Expired
            "debit_order_returns": ["account_closed"],
        }
        collection = {
            "collection_amount": 5000.00,
            "collection_due_date": date(2026, 4, 28),
        }
        result = engine.score("CARD_DEBIT", customer, collection)
        assert result.risk_level == "HIGH"
        assert result.recommended_action == "flag_for_review"

    def test_custom_weights(self, sa_customer_data, sa_collection_data):
        custom = {"historical_failure_rate": 0.5, "day_of_month_vs_payday": 0.5}
        result = engine.score(
            "CARD_DEBIT", sa_customer_data, sa_collection_data, custom_weights=custom
        )
        for f in result.factors:
            if f.factor_name == "historical_failure_rate":
                assert f.weight == 0.5
            elif f.factor_name == "day_of_month_vs_payday":
                assert f.weight == 0.5

    def test_empty_customer_data(self, sa_collection_data):
        result = engine.score("CARD_DEBIT", {}, sa_collection_data)
        assert len(result.factors) == 8
        assert 0.0 <= result.score <= 1.0


class TestScoringEngineWallet:
    def test_scores_all_8_wallet_factors(self, zm_customer_data, zm_collection_data):
        result = engine.score("MOBILE_WALLET", zm_customer_data, zm_collection_data)
        assert len(result.factors) == 8
        assert 0.0 <= result.score <= 1.0
        assert result.model_version == "heuristic_wallet_v1"

    def test_factor_names(self, zm_customer_data, zm_collection_data):
        result = engine.score("MOBILE_WALLET", zm_customer_data, zm_collection_data)
        names = {f.factor_name for f in result.factors}
        expected = {
            "wallet_balance_trend", "historical_failure_rate",
            "time_since_last_inflow", "salary_cycle_alignment",
            "concurrent_loan_count", "transaction_velocity",
            "airtime_purchase_pattern", "loan_cycling_behaviour",
        }
        assert names == expected

    def test_empty_customer_data(self, zm_collection_data):
        result = engine.score("MOBILE_WALLET", {}, zm_collection_data)
        assert len(result.factors) == 8


class TestRiskMapping:
    def test_low(self):
        assert engine._map_risk_level(0.15) == "LOW"

    def test_medium(self):
        assert engine._map_risk_level(0.45) == "MEDIUM"

    def test_high(self):
        assert engine._map_risk_level(0.75) == "HIGH"

    def test_boundary_low_medium(self):
        assert engine._map_risk_level(0.30) == "LOW"
        assert engine._map_risk_level(0.31) == "MEDIUM"

    def test_boundary_medium_high(self):
        assert engine._map_risk_level(0.60) == "MEDIUM"
        assert engine._map_risk_level(0.61) == "HIGH"


class TestInvalidFactorSet:
    def test_unknown_factor_set(self):
        import pytest
        with pytest.raises(ValueError, match="Unknown factor set"):
            engine.score("INVALID", {}, {})
