// Risk level configuration — SINGLE SOURCE OF TRUTH
// Uses alpha-style backgrounds so colors work in both light and dark modes.
export const RISK_CONFIG = {
  HIGH: {
    label: "High",
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    dot: "bg-red-500",
    bar: "bg-red-500",
    barColor: "#ef4444",
    range: [61, 100],
  },
  MEDIUM: {
    label: "Medium",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    dot: "bg-amber-500",
    bar: "bg-amber-500",
    barColor: "#f59e0b",
    range: [31, 60],
  },
  LOW: {
    label: "Low",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    dot: "bg-emerald-500",
    bar: "bg-emerald-500",
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
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
  },
  DEBIT_ORDER: {
    label: "Debit Order",
    icon: "Building",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "border-purple-500/30",
  },
  MOBILE_MONEY: {
    label: "Mobile Money",
    icon: "Smartphone",
    color: "text-orange-400",
    bg: "bg-orange-500/10",
    border: "border-orange-500/30",
  },
} as const;

// Role badge configuration — SINGLE SOURCE OF TRUTH
export const ROLE_CONFIG = {
  ADMIN: {
    label: "Admin",
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
  },
  MANAGER: {
    label: "Manager",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
  },
  VIEWER: {
    label: "Viewer",
    color: "text-zinc-400",
    bg: "bg-zinc-500/10",
    border: "border-zinc-500/30",
  },
} as const;

// Recharts theme — SINGLE SOURCE OF TRUTH
// All chart components must reference these — never hardcode colors in charts.
export const CHART_THEME = {
  grid: "rgba(161, 161, 170, 0.15)", // zinc-400 at 15%
  axis: "rgb(161, 161, 170)", // zinc-400
  tooltipBg: "rgb(24, 24, 27)", // zinc-900
  tooltipBorder: "rgb(63, 63, 70)", // zinc-700
  tooltipText: "rgb(244, 244, 245)", // zinc-100
  high: "#ef4444", // red-500
  medium: "#f59e0b", // amber-500
  low: "#10b981", // emerald-500
  primary: "#10b981", // emerald-500 — default line/bar
  secondary: "#6366f1", // indigo-500 — second series
  muted: "rgba(161, 161, 170, 0.3)", // zinc-400 at 30%
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
