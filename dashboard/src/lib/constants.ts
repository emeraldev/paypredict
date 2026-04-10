// Risk level configuration — SINGLE SOURCE OF TRUTH
export const RISK_CONFIG = {
  HIGH: {
    label: "High",
    color: "text-red-400",
    bg: "bg-red-950",
    border: "border-red-500",
    dot: "bg-red-500",
    barColor: "#ef4444",
    range: [61, 100],
  },
  MEDIUM: {
    label: "Medium",
    color: "text-amber-400",
    bg: "bg-amber-950",
    border: "border-amber-500",
    dot: "bg-amber-500",
    barColor: "#f59e0b",
    range: [31, 60],
  },
  LOW: {
    label: "Low",
    color: "text-emerald-400",
    bg: "bg-emerald-950",
    border: "border-emerald-500",
    dot: "bg-emerald-500",
    barColor: "#10b981",
    range: [0, 30],
  },
} as const;

// Score thresholds matching backend engine (_map_risk_level)
// Backend uses: <=0.30 LOW, <=0.60 MEDIUM, else HIGH
export const RISK_THRESHOLDS = {
  LOW_MAX: 30, // display score (0-100), <=30 = LOW
  MEDIUM_MAX: 60, // display score (0-100), <=60 = MEDIUM, else HIGH
} as const;

// Collection method configuration — SINGLE SOURCE OF TRUTH
export const METHOD_CONFIG = {
  CARD: {
    label: "Card",
    icon: "CreditCard",
    color: "text-blue-400",
    bg: "bg-blue-950",
    border: "border-blue-500",
  },
  DEBIT_ORDER: {
    label: "Debit Order",
    icon: "Building",
    color: "text-purple-400",
    bg: "bg-purple-950",
    border: "border-purple-500",
  },
  MOBILE_MONEY: {
    label: "Mobile Money",
    icon: "Smartphone",
    color: "text-orange-400",
    bg: "bg-orange-950",
    border: "border-orange-500",
  },
} as const;

// Factor descriptions for the settings page
export const FACTOR_DESCRIPTIONS: Record<string, string> = {
  historical_failure_rate: "Past payment success/failure ratio",
  day_of_month_vs_payday: "Alignment with salary timing",
  days_since_last_payment: "Recency of last successful payment",
  instalment_position: "Position in the instalment plan",
  order_value_vs_average: "Collection amount vs customer history",
  card_health: "Card expiry and decline history",
  card_type: "Credit vs debit card risk",
  debit_order_return_history: "EFT return code patterns",
  wallet_balance_trend: "7-day wallet balance direction",
  time_since_last_inflow: "Hours since last wallet top-up",
  salary_cycle_alignment: "Collection vs income timing",
  concurrent_loan_count: "Number of active loans",
  transaction_velocity: "Recent transaction activity changes",
  airtime_purchase_pattern: "Airtime buying regularity",
  loan_cycling_behaviour: "Borrowing to repay pattern",
};

// Friendly factor display names
export const FACTOR_LABELS: Record<string, string> = {
  historical_failure_rate: "Historical Failure Rate",
  day_of_month_vs_payday: "Day of Month vs Payday",
  days_since_last_payment: "Days Since Last Payment",
  instalment_position: "Instalment Position",
  order_value_vs_average: "Order Value vs Average",
  card_health: "Card Health",
  card_type: "Card Type",
  debit_order_return_history: "Debit Order Return History",
  wallet_balance_trend: "Wallet Balance Trend",
  time_since_last_inflow: "Time Since Last Inflow",
  salary_cycle_alignment: "Salary Cycle Alignment",
  concurrent_loan_count: "Concurrent Loan Count",
  transaction_velocity: "Transaction Velocity",
  airtime_purchase_pattern: "Airtime Purchase Pattern",
  loan_cycling_behaviour: "Loan Cycling Behaviour",
};
