from app.models.score_request import CollectionMethod
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

# Payroll factors (Zambia salary-advance lenders)
from app.scoring.factors.payroll.threshold_headroom import ThresholdHeadroom
from app.scoring.factors.payroll.deduction_to_income import DeductionToIncomeRatio
from app.scoring.factors.payroll.resubmission_history import ResubmissionHistory
from app.scoring.factors.payroll.borrower_segment import BorrowerSegment


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

# Payroll deduction (salary advances, initially Zambia). Threshold headroom
# dominates — that's the regulatory rejection mechanism. Concurrent loans is
# heavily weighted because "someone else's deduction consumed the headroom"
# is the same failure mode. Segment sits low because it's a coarse prior.
PAYROLL_FACTORS: dict[str, FactorEntry] = {
    "threshold_headroom": (ThresholdHeadroom(), 0.25),
    "historical_failure_rate": (HistoricalFailureRate(), 0.20),
    "deduction_to_income_ratio": (DeductionToIncomeRatio(), 0.15),
    "concurrent_loan_count": (ConcurrentLoanCount(), 0.15),
    "resubmission_history": (ResubmissionHistory(), 0.10),
    "borrower_segment": (BorrowerSegment(), 0.05),
    "loan_cycling_behaviour": (LoanCyclingBehaviour(), 0.05),
    "instalment_position": (InstalmentPosition(), 0.05),
}

# DEPRECATED: kept for backward compat with any caller that still passes a
# tenant.factor_set string. The primary lookup is now by CollectionMethod via
# METHOD_FACTOR_SETS below. Will be removed once the deprecation window
# passes and no external caller relies on the string form.
FACTOR_REGISTRY: dict[str, dict[str, FactorEntry]] = {
    "CARD_DEBIT": CARD_DEBIT_FACTORS,
    "MOBILE_WALLET": MOBILE_WALLET_FACTORS,
    "PAYROLL": PAYROLL_FACTORS,
}


# Primary lookup: which factor bundle applies to which collection method.
# CARD and DEBIT_ORDER share the same underlying bundle (CARD_DEBIT_FACTORS);
# the per-factor `applicable_methods` filter still handles skipping
# CardHealth/CardType for debit orders and DebitOrderReturnHistory for cards,
# same as before — no factor logic changes with this mapping.
METHOD_FACTOR_SETS: dict[CollectionMethod, dict[str, FactorEntry]] = {
    CollectionMethod.CARD: CARD_DEBIT_FACTORS,
    CollectionMethod.DEBIT_ORDER: CARD_DEBIT_FACTORS,
    CollectionMethod.MOBILE_MONEY: MOBILE_WALLET_FACTORS,
    CollectionMethod.PAYROLL: PAYROLL_FACTORS,
}


def get_factors_for_method(
    method: CollectionMethod,
) -> dict[str, FactorEntry]:
    """Return factor instances + default weights for a collection method.

    Every scoring request already carries `collection_method`; this is the
    canonical way to pick the factor bundle. Replaces `get_factors_for_set`
    for all new scoring code paths.
    """
    factors = METHOD_FACTOR_SETS.get(method)
    if factors is None:
        raise ValueError(f"No factor bundle registered for method: {method}")
    return factors


def get_default_weights_for_method(
    method: CollectionMethod,
) -> dict[str, float]:
    """Return default weights per factor for a collection method."""
    factors = get_factors_for_method(method)
    return {name: weight for name, (_, weight) in factors.items()}


def get_factors_for_set(factor_set: str) -> dict[str, FactorEntry]:
    """DEPRECATED: use `get_factors_for_method` instead. Kept so any legacy
    caller passing a factor_set string keeps working during the migration
    window."""
    factors = FACTOR_REGISTRY.get(factor_set)
    if factors is None:
        raise ValueError(f"Unknown factor set: {factor_set}")
    return factors


def get_default_weights(factor_set: str) -> dict[str, float]:
    """DEPRECATED: use `get_default_weights_for_method`."""
    factors = get_factors_for_set(factor_set)
    return {name: weight for name, (_, weight) in factors.items()}


# Plain-English display names + one-liner descriptions for every factor
# name across every bundle. Surfaced in the weights API response so the
# dashboard and integrators see the same wording without duplicating the
# mapping. Must stay in sync with the dashboard's FACTOR_LABELS /
# FACTOR_DESCRIPTIONS (the dashboard falls back to these client-side
# copies if the API happens to add a new factor before the frontend ships).
FACTOR_LABELS: dict[str, str] = {
    "historical_failure_rate": "Past failure rate",
    "day_of_month_vs_payday": "Date vs payday",
    "days_since_last_payment": "Days since last payment",
    "instalment_position": "Where in the instalment plan",
    "order_value_vs_average": "Amount vs customer typical",
    "card_health": "Card health (expiry & declines)",
    "card_type": "Card type (debit/credit)",
    "debit_order_return_history": "Past debit order returns",
    "wallet_balance_trend": "Wallet balance trend",
    "time_since_last_inflow": "Time since last wallet inflow",
    "salary_cycle_alignment": "Aligned with income timing",
    "concurrent_loan_count": "Active loans count",
    "transaction_velocity": "Wallet activity change",
    "airtime_purchase_pattern": "Airtime buying regularity",
    "loan_cycling_behaviour": "Loan stacking pattern",
    "threshold_headroom": "Salary threshold headroom",
    "deduction_to_income_ratio": "Deduction vs income",
    "resubmission_history": "Deduction resubmission history",
    "borrower_segment": "Employment sector",
}


FACTOR_DESCRIPTIONS: dict[str, str] = {
    "historical_failure_rate": "Past payment success/failure ratio",
    "day_of_month_vs_payday": "Alignment with salary timing",
    "days_since_last_payment": "Recency of last successful payment",
    "instalment_position": "Position in the instalment plan",
    "order_value_vs_average": "Collection amount vs customer history",
    "card_health": "Card expiry and decline history",
    "card_type": "Credit vs debit card risk",
    "debit_order_return_history": "EFT return code patterns",
    "wallet_balance_trend": "7-day wallet balance direction",
    "time_since_last_inflow": "Hours since last wallet top-up",
    "salary_cycle_alignment": "Collection vs income timing",
    "concurrent_loan_count": "Number of active loans",
    "transaction_velocity": "Recent transaction activity changes",
    "airtime_purchase_pattern": "Airtime buying regularity",
    "loan_cycling_behaviour": "Borrowing to repay pattern",
    "threshold_headroom": "Room before hitting the regulatory deduction cap",
    "deduction_to_income_ratio": "Deduction size relative to borrower's income",
    "resubmission_history": "Past deductions resubmitted at lower amounts",
    "borrower_segment": "Employment sector risk (government/mining/private)",
}


METHOD_LABELS: dict[CollectionMethod, str] = {
    CollectionMethod.CARD: "Card",
    CollectionMethod.DEBIT_ORDER: "Debit Order",
    CollectionMethod.MOBILE_MONEY: "Mobile Money",
    CollectionMethod.PAYROLL: "Payroll",
}
