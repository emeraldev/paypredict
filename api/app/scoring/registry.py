from app.scoring.factors.base import BaseFactor

# Shared factors (used by multiple factor sets)
from app.scoring.factors.shared.historical_failure import HistoricalFailureRate
from app.scoring.factors.shared.instalment_position import InstalmentPosition
from app.scoring.factors.shared.concurrent_loans import ConcurrentLoanCount
from app.scoring.factors.shared.loan_cycling import LoanCyclingBehaviour

# Card/debit order factors
from app.scoring.factors.card.day_of_month import DayOfMonthVsPayday
from app.scoring.factors.card.days_since_payment import DaysSinceLastPayment
from app.scoring.factors.card.order_value import OrderValueVsAverage
from app.scoring.factors.card.card_health import CardHealth
from app.scoring.factors.card.card_type import CardType
from app.scoring.factors.card.debit_order_returns import DebitOrderReturnHistory

# Mobile wallet factors
from app.scoring.factors.wallet.wallet_balance_trend import WalletBalanceTrend
from app.scoring.factors.wallet.time_since_inflow import TimeSinceLastInflow
from app.scoring.factors.wallet.salary_cycle import SalaryCycleAlignment
from app.scoring.factors.wallet.transaction_velocity import TransactionVelocity
from app.scoring.factors.wallet.airtime_pattern import AirtimePurchasePattern


# Factor name → (factor instance, default weight)
FactorEntry = tuple[BaseFactor, float]

CARD_DEBIT_FACTORS: dict[str, FactorEntry] = {
    "historical_failure_rate": (HistoricalFailureRate(), 0.25),
    "day_of_month_vs_payday": (DayOfMonthVsPayday(), 0.20),
    "days_since_last_payment": (DaysSinceLastPayment(), 0.15),
    "instalment_position": (InstalmentPosition(), 0.10),
    "order_value_vs_average": (OrderValueVsAverage(), 0.10),
    "card_health": (CardHealth(), 0.10),
    "card_type": (CardType(), 0.05),
    "debit_order_return_history": (DebitOrderReturnHistory(), 0.05),
}

MOBILE_WALLET_FACTORS: dict[str, FactorEntry] = {
    "wallet_balance_trend": (WalletBalanceTrend(), 0.25),
    "historical_failure_rate": (HistoricalFailureRate(), 0.20),
    "time_since_last_inflow": (TimeSinceLastInflow(), 0.15),
    "salary_cycle_alignment": (SalaryCycleAlignment(), 0.15),
    "concurrent_loan_count": (ConcurrentLoanCount(), 0.10),
    "transaction_velocity": (TransactionVelocity(), 0.05),
    "airtime_purchase_pattern": (AirtimePurchasePattern(), 0.05),
    "loan_cycling_behaviour": (LoanCyclingBehaviour(), 0.05),
}

FACTOR_REGISTRY: dict[str, dict[str, FactorEntry]] = {
    "CARD_DEBIT": CARD_DEBIT_FACTORS,
    "MOBILE_WALLET": MOBILE_WALLET_FACTORS,
}


def get_factors_for_set(factor_set: str) -> dict[str, FactorEntry]:
    """Return factor instances and default weights for a factor set."""
    factors = FACTOR_REGISTRY.get(factor_set)
    if factors is None:
        raise ValueError(f"Unknown factor set: {factor_set}")
    return factors


def get_default_weights(factor_set: str) -> dict[str, float]:
    """Return default weights for a factor set."""
    factors = get_factors_for_set(factor_set)
    return {name: weight for name, (_, weight) in factors.items()}
