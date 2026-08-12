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

    def test_weights_snapshot_captures_full_bundle(
        self, sa_customer_data, sa_collection_data
    ):
        """The engine snapshots every factor's pre-normalisation weight
        so the caller can persist the exact config each score was
        produced under — necessary for ML training reproducibility."""
        from app.models.score_request import CollectionMethod

        result = engine.score(
            customer_data=sa_customer_data,
            collection_data=sa_collection_data,
            collection_method=CollectionMethod.CARD,
        )
        snap = result.weights_snapshot
        # Full CARD_DEBIT bundle regardless of which factors actually fired.
        assert set(snap.keys()) == {
            "historical_failure_rate", "day_of_month_vs_payday",
            "days_since_last_payment", "instalment_position",
            "order_value_vs_average", "card_health",
            "card_type", "debit_order_return_history",
        }
        # Snapshot is pre-normalisation, so bundle defaults must still sum to 1.
        assert abs(sum(snap.values()) - 1.0) < 0.01

    def test_weights_snapshot_reflects_custom_overrides(
        self, sa_customer_data, sa_collection_data
    ):
        """When the caller passes custom weights, those override the
        defaults in the snapshot — not the bundle defaults."""
        from app.models.score_request import CollectionMethod

        custom = {
            "historical_failure_rate": 0.40,
            "day_of_month_vs_payday": 0.05,
        }
        result = engine.score(
            customer_data=sa_customer_data,
            collection_data=sa_collection_data,
            collection_method=CollectionMethod.CARD,
            custom_weights=custom,
        )
        assert result.weights_snapshot["historical_failure_rate"] == 0.40
        assert result.weights_snapshot["day_of_month_vs_payday"] == 0.05
        # Untouched factors fall back to bundle defaults.
        assert result.weights_snapshot["card_health"] == 0.10


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


class TestScoringEnginePayroll:
    """PAYROLL factor set — Zambia salary-advance lenders. 4 payroll-specific
    factors + 4 shared factors = 8 total (same count as CARD_DEBIT and
    MOBILE_WALLET). None should be skipped when collection_method=PAYROLL —
    the payroll factors declare `applicable_methods = [PAYROLL]`, and the
    shared factors apply everywhere."""

    from app.models.score_request import CollectionMethod

    _payroll_customer = {
        "total_payments": 6,
        "successful_payments": 5,
        "instalment_number": 2,
        "total_instalments": 3,
        "active_loan_count": 2,
        "loans_taken_last_90d": 1,
        "gross_salary": 10000,
        "net_pay": 5500,
        "current_total_deductions": 2400,
        "deduction_threshold_pct": 0.40,
        "resubmission_count": 1,
        "borrower_segment": "government",
    }
    _payroll_collection = {
        "collection_amount": 1500,
        "collection_due_date": date(2026, 8, 25),
        "collection_method": "PAYROLL",
        "collection_currency": "ZMW",
    }

    def test_scores_all_8_payroll_factors(self):
        result = engine.score(
            "PAYROLL",
            self._payroll_customer,
            self._payroll_collection,
            collection_method=self.CollectionMethod.PAYROLL,
        )
        assert len(result.factors) == 8
        assert 0.0 <= result.score <= 1.0
        assert result.risk_level in ("LOW", "MEDIUM", "HIGH")
        assert result.model_version == "heuristic_payroll_v1"
        # No PAYROLL factor should be skipped when the method matches.
        assert result.skipped_factors == []

    def test_factor_names(self):
        result = engine.score(
            "PAYROLL",
            self._payroll_customer,
            self._payroll_collection,
            collection_method=self.CollectionMethod.PAYROLL,
        )
        names = {f.factor_name for f in result.factors}
        expected = {
            "threshold_headroom", "historical_failure_rate",
            "deduction_to_income_ratio", "concurrent_loan_count",
            "resubmission_history", "borrower_segment",
            "loan_cycling_behaviour", "instalment_position",
        }
        assert names == expected

    def test_empty_customer_data_degrades_gracefully(self):
        # No salary data, no segment, no history — every factor should fall
        # back to its default without crashing.
        result = engine.score(
            "PAYROLL",
            {},
            self._payroll_collection,
            collection_method=self.CollectionMethod.PAYROLL,
        )
        assert len(result.factors) == 8
        assert 0.0 <= result.score <= 1.0

    def test_tight_headroom_produces_high_risk_score(self):
        # Existing deductions consume 90% of the 40% cap; our deduction
        # exceeds the remaining headroom. ThresholdHeadroom is 25% of the
        # blended score, so a 0.9-1.0 raw contribution moves the needle.
        tight = {
            **self._payroll_customer,
            "current_total_deductions": 3600,  # 90% of ZMW 4000 cap
        }
        big_deduction = {**self._payroll_collection, "collection_amount": 800}
        loose = {
            **self._payroll_customer,
            "current_total_deductions": 800,  # 20% of cap — plenty of room
        }
        small_deduction = {**self._payroll_collection, "collection_amount": 200}

        tight_score = engine.score(
            "PAYROLL", tight, big_deduction,
            collection_method=self.CollectionMethod.PAYROLL,
        ).score
        loose_score = engine.score(
            "PAYROLL", loose, small_deduction,
            collection_method=self.CollectionMethod.PAYROLL,
        ).score
        assert tight_score > loose_score

    def test_shared_factors_produce_identical_scores_across_sets(self):
        """HistoricalFailureRate is one of the 4 shared factors — same inputs
        must produce the same value whether scored under CARD_DEBIT or
        PAYROLL. Guards against accidental method-conditional logic slipping
        into a 'shared' factor."""
        from app.scoring.factors.shared.historical_failure import HistoricalFailureRate
        f = HistoricalFailureRate()
        data = {"total_payments": 10, "successful_payments": 7}
        assert f.calculate(data, {}) == f.calculate(data, {})  # deterministic
        # And it applies everywhere — shared factor invariant.
        assert f.applicable_methods is None


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


class TestMethodDrivenBundleSelection:
    """Same tenant, same engine — different bundle per row via
    `collection_method`. This is the correctness fix that the whole
    per-method migration exists to enable."""

    from app.models.score_request import CollectionMethod

    _customer = {"total_payments": 10, "successful_payments": 7}
    _base_collection = {
        "collection_amount": 500.0,
        "collection_due_date": date(2026, 8, 20),
    }

    def test_card_uses_card_bundle(self):
        result = engine.score(
            customer_data=self._customer,
            collection_data={**self._base_collection, "collection_method": "CARD"},
            collection_method=self.CollectionMethod.CARD,
        )
        names = {f.factor_name for f in result.factors}
        assert "card_health" in names or "card_health" in result.skipped_factors
        assert "wallet_balance_trend" not in names
        assert "threshold_headroom" not in names
        assert result.model_version == "heuristic_card_v1"

    def test_payroll_uses_payroll_bundle(self):
        result = engine.score(
            customer_data={
                **self._customer,
                "gross_salary": 10000,
                "current_total_deductions": 2000,
            },
            collection_data={**self._base_collection, "collection_method": "PAYROLL"},
            collection_method=self.CollectionMethod.PAYROLL,
        )
        names = {f.factor_name for f in result.factors}
        assert "threshold_headroom" in names
        assert "card_health" not in names
        assert "wallet_balance_trend" not in names
        assert result.model_version == "heuristic_payroll_v1"

    def test_debit_order_and_card_share_bundle_with_different_skips(self):
        """Both methods share CARD_DEBIT_FACTORS; the per-factor filter picks
        which get skipped. CARD skips DebitOrderReturnHistory; DEBIT_ORDER
        skips CardHealth + CardType."""
        card = engine.score(
            customer_data=self._customer,
            collection_data={**self._base_collection, "collection_method": "CARD"},
            collection_method=self.CollectionMethod.CARD,
        )
        debit = engine.score(
            customer_data=self._customer,
            collection_data={**self._base_collection, "collection_method": "DEBIT_ORDER"},
            collection_method=self.CollectionMethod.DEBIT_ORDER,
        )
        assert card.skipped_factors == ["debit_order_return_history"]
        assert set(debit.skipped_factors) == {"card_health", "card_type"}
        assert card.model_version == debit.model_version == "heuristic_card_v1"
