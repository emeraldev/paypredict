"""Unit tests for the timing optimiser.

We test the optimiser against the real ScoringEngine — the optimiser is
just a search loop, so the only thing worth verifying is that it picks
the right candidate, respects the threshold, skips past dates, and
no-ops when no improvement exists.
"""
from datetime import date

import pytest

from app.models.score_request import CollectionMethod
from app.scoring.engine import ScoringEngine
from app.scoring.timing_optimiser import (
    SEARCH_WINDOW_DAYS,
    SHIFT_THRESHOLD,
    optimise_collection_date,
)


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine()


def _score(engine: ScoringEngine, customer: dict, due_date: date) -> float:
    return engine.score(
        factor_set="CARD_DEBIT",
        customer_data=customer,
        collection_data={
            "collection_amount": 1500.0,
            "collection_due_date": due_date,
            "collection_method": "CARD",
            "collection_currency": "ZAR",
        },
        collection_method=CollectionMethod.CARD,
    ).score


def test_recommends_shift_to_just_after_payday(engine):
    """Customer with salary day 25 + due date on the 24th (one day BEFORE
    payday — the worst-risk timing window: days_after = 30, score 0.8).
    Optimiser should shift forward by 1-3 days into the lowest-risk
    window where the factor returns 0.1.

    The weighted swing on the timing factor alone (0.20 × 0.7 = 0.14)
    clears the 0.10 SHIFT_THRESHOLD even after other factors stay flat.
    """
    customer = {
        "known_salary_day": 25,
        "total_payments": 10,
        "successful_payments": 8,
        "card_type": "debit",
    }
    original = date(2026, 4, 24)  # 1 day before payday — worst window
    original_score = _score(engine, customer, original)

    result = optimise_collection_date(
        engine,
        factor_set="CARD_DEBIT",
        customer_data=customer,
        collection_data={
            "collection_amount": 1500.0,
            "collection_due_date": original,
            "collection_method": "CARD",
            "collection_currency": "ZAR",
        },
        collection_method=CollectionMethod.CARD,
        original_score=original_score,
        today=date(2026, 4, 1),
    )

    assert result.should_shift is True, (
        f"Expected a shift recommendation; got {result}. Original score: {original_score}"
    )
    # Recommended date should land in [salary_day, salary_day + 3] — the
    # lowest-risk window.
    assert result.recommended_date is not None
    assert 25 <= result.recommended_date.day <= 28
    assert result.score_improvement >= SHIFT_THRESHOLD
    assert result.recommended_score is not None
    assert result.recommended_score < original_score


def test_no_shift_when_original_is_already_optimal(engine):
    """Customer with salary day 25 + due date on the 26th is in the
    lowest-risk window already; no day in the ±14 search produces a
    meaningful improvement."""
    customer = {
        "known_salary_day": 25,
        "total_payments": 10,
        "successful_payments": 8,
        "card_type": "debit",
    }
    original = date(2026, 4, 26)
    original_score = _score(engine, customer, original)

    result = optimise_collection_date(
        engine,
        factor_set="CARD_DEBIT",
        customer_data=customer,
        collection_data={
            "collection_amount": 1500.0,
            "collection_due_date": original,
            "collection_method": "CARD",
            "collection_currency": "ZAR",
        },
        collection_method=CollectionMethod.CARD,
        original_score=original_score,
        today=date(2026, 4, 1),
    )

    assert result.should_shift is False
    assert result.recommended_date is None
    assert result.recommended_score is None
    assert result.score_improvement == 0.0


def test_skips_past_dates(engine):
    """Candidate dates before `today` are excluded from the search."""
    customer = {"known_salary_day": 25, "total_payments": 10, "successful_payments": 8, "card_type": "debit"}
    original = date(2026, 4, 28)
    original_score = _score(engine, customer, original)

    # Today == original - 1: only one day in the past would have been
    # better (the 25th), but it's filtered out by the floor.
    result = optimise_collection_date(
        engine,
        factor_set="CARD_DEBIT",
        customer_data=customer,
        collection_data={
            "collection_amount": 1500.0,
            "collection_due_date": original,
            "collection_method": "CARD",
            "collection_currency": "ZAR",
        },
        collection_method=CollectionMethod.CARD,
        original_score=original_score,
        today=date(2026, 4, 27),
    )

    # If a shift IS recommended, it must not be in the past.
    if result.recommended_date is not None:
        assert result.recommended_date >= date(2026, 4, 27)


def test_no_date_dependent_factors_returns_no_shift(engine):
    """If we strip both date-dependent factors via custom_weights set to 0,
    every candidate scores the same as the original — no shift."""
    customer = {
        "known_salary_day": 25,
        "total_payments": 10,
        "successful_payments": 8,
        "card_type": "debit",
    }
    original = date(2026, 4, 30)
    # Zero out the only date-dependent factor for CARD_DEBIT.
    zero_date_factor_weights = {"day_of_month_vs_payday": 0.0}
    original_score = engine.score(
        factor_set="CARD_DEBIT",
        customer_data=customer,
        collection_data={
            "collection_amount": 1500.0,
            "collection_due_date": original,
            "collection_method": "CARD",
            "collection_currency": "ZAR",
        },
        custom_weights=zero_date_factor_weights,
        collection_method=CollectionMethod.CARD,
    ).score

    result = optimise_collection_date(
        engine,
        factor_set="CARD_DEBIT",
        customer_data=customer,
        collection_data={
            "collection_amount": 1500.0,
            "collection_due_date": original,
            "collection_method": "CARD",
            "collection_currency": "ZAR",
        },
        collection_method=CollectionMethod.CARD,
        original_score=original_score,
        custom_weights=zero_date_factor_weights,
        today=date(2026, 4, 1),
    )

    assert result.should_shift is False
    assert result.score_improvement == 0.0


def test_search_window_covers_at_most_28_extra_evaluations(engine):
    """Sanity: with default ±14 days, we never evaluate more than 28
    candidates (we skip delta=0). This guards the documented latency
    budget."""
    assert SEARCH_WINDOW_DAYS == 14
    assert SHIFT_THRESHOLD == 0.10


def test_threshold_keeps_trivial_improvements_silent(engine, monkeypatch):
    """When the best improvement is below SHIFT_THRESHOLD we don't
    surface it — tested by temporarily raising the threshold."""
    from app.scoring import timing_optimiser

    monkeypatch.setattr(timing_optimiser, "SHIFT_THRESHOLD", 0.95)

    customer = {
        "known_salary_day": 25,
        "total_payments": 10,
        "successful_payments": 8,
        "card_type": "debit",
    }
    original = date(2026, 4, 30)
    original_score = _score(engine, customer, original)

    result = optimise_collection_date(
        engine,
        factor_set="CARD_DEBIT",
        customer_data=customer,
        collection_data={
            "collection_amount": 1500.0,
            "collection_due_date": original,
            "collection_method": "CARD",
            "collection_currency": "ZAR",
        },
        collection_method=CollectionMethod.CARD,
        original_score=original_score,
        today=date(2026, 4, 1),
    )

    # The model improves by ~0.18 here — well below the artificial 0.95
    # cutoff, so the recommendation must be suppressed.
    assert result.should_shift is False
    assert result.recommended_date is None


def test_wallet_factor_set_with_inflow_day(engine):
    """MOBILE_WALLET set uses regular_inflow_day, not known_salary_day.
    Verify the optimiser shifts toward the inflow day for that set."""
    customer = {
        "regular_inflow_day": "friday",
        "total_payments": 8,
        "successful_payments": 6,
        "wallet_balance_current": 500.0,
        "wallet_balance_7d_avg": 600.0,
    }
    # Original due on Wednesday — 5 days after Friday. Should shift
    # toward a Friday or Saturday.
    original = date(2026, 4, 8)  # Wednesday
    original_score = engine.score(
        factor_set="MOBILE_WALLET",
        customer_data=customer,
        collection_data={
            "collection_amount": 250.0,
            "collection_due_date": original,
            "collection_method": "MOBILE_MONEY",
            "collection_currency": "ZMW",
        },
        collection_method=CollectionMethod.MOBILE_MONEY,
    ).score

    result = optimise_collection_date(
        engine,
        factor_set="MOBILE_WALLET",
        customer_data=customer,
        collection_data={
            "collection_amount": 250.0,
            "collection_due_date": original,
            "collection_method": "MOBILE_MONEY",
            "collection_currency": "ZMW",
        },
        collection_method=CollectionMethod.MOBILE_MONEY,
        original_score=original_score,
        today=date(2026, 4, 1),
    )

    if result.should_shift:
        # Recommended date should land on a Friday (4) or Saturday (5).
        assert result.recommended_date.weekday() in (4, 5), (
            f"Expected Fri/Sat alignment for Friday inflow, got "
            f"{result.recommended_date} ({result.recommended_date.weekday()})"
        )
