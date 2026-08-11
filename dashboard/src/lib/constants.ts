// Risk level configuration — SINGLE SOURCE OF TRUTH
// Class values reference the semantic tokens defined in globals.css so
// light/dark theming happens at the CSS layer, not here.
export const RISK_CONFIG = {
  HIGH: {
    label: "High",
    color: "text-risk-high-fg",
    bg: "bg-risk-high-bg",
    border: "border-risk-high/30",
    dot: "bg-risk-high",
    bar: "bg-risk-high",
    barColor: "var(--color-risk-high)",
    range: [61, 100],
  },
  MEDIUM: {
    label: "Medium",
    color: "text-risk-med-fg",
    bg: "bg-risk-med-bg",
    border: "border-risk-med/30",
    dot: "bg-risk-med",
    bar: "bg-risk-med",
    barColor: "var(--color-risk-med)",
    range: [31, 60],
  },
  LOW: {
    label: "Low",
    color: "text-risk-low-fg",
    bg: "bg-risk-low-bg",
    border: "border-risk-low/30",
    dot: "bg-risk-low",
    bar: "bg-risk-low",
    barColor: "var(--color-risk-low)",
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
// New look: neutral pill (bg-muted, text-foreground) with a small
// colored dot for method identity. The saturated per-method fills
// were dropped to reduce visual noise on data-dense tables.
export const METHOD_CONFIG = {
  CARD: {
    label: "Card",
    icon: "CreditCard",
    color: "text-foreground",
    bg: "bg-muted",
    border: "border-border",
    dot: "bg-method-card",
    dotColor: "var(--color-method-card)",
  },
  DEBIT_ORDER: {
    label: "Debit Order",
    icon: "Building",
    color: "text-foreground",
    bg: "bg-muted",
    border: "border-border",
    dot: "bg-method-debit",
    dotColor: "var(--color-method-debit)",
  },
  MOBILE_MONEY: {
    label: "Mobile Money",
    icon: "Smartphone",
    color: "text-foreground",
    bg: "bg-muted",
    border: "border-border",
    dot: "bg-method-mobile",
    dotColor: "var(--color-method-mobile)",
  },
  PAYROLL: {
    label: "Payroll",
    icon: "Landmark",
    color: "text-foreground",
    bg: "bg-muted",
    border: "border-border",
    dot: "bg-method-payroll",
    dotColor: "var(--color-method-payroll)",
  },
} as const;

// Role badge configuration — SINGLE SOURCE OF TRUTH
// Neutral pill with a small colored dot, same pattern as METHOD_CONFIG.
export const ROLE_CONFIG = {
  ADMIN: {
    label: "Admin",
    color: "text-foreground",
    bg: "bg-muted",
    border: "border-border",
    dot: "bg-risk-high",
  },
  MANAGER: {
    label: "Manager",
    color: "text-foreground",
    bg: "bg-muted",
    border: "border-border",
    dot: "bg-primary",
  },
  VIEWER: {
    label: "Viewer",
    color: "text-foreground",
    bg: "bg-muted",
    border: "border-border",
    dot: "bg-muted-foreground",
  },
} as const;

// Recharts theme — SINGLE SOURCE OF TRUTH
// All chart components must reference these; never hardcode colors in charts.
// Values point at CSS variables so a theme flip re-tints charts too, as long
// as Recharts renders the SVG in the same document (it does — no shadow DOM).
export const CHART_THEME = {
  grid: "var(--color-border)",
  axis: "var(--color-muted-foreground)",
  tooltipBg: "var(--color-popover)",
  tooltipBorder: "var(--color-border)",
  tooltipText: "var(--color-popover-foreground)",
  high: "var(--color-risk-high)",
  medium: "var(--color-risk-med)",
  low: "var(--color-risk-low)",
  primary: "var(--color-chart-1)",
  secondary: "var(--color-chart-2)",
  muted: "var(--color-muted-foreground)",
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
  // PAYROLL factor set
  threshold_headroom: "Room before hitting the regulatory deduction cap",
  deduction_to_income_ratio: "Deduction size relative to borrower's income",
  resubmission_history: "Past deductions resubmitted at lower amounts",
  borrower_segment: "Employment sector risk (government/mining/private)",
};

// Ordered factor list per collection method — mirrors the backend
// registry order. Only used as a defensive local fallback: the API
// response already carries labels + order per method, so components
// should prefer the API's `factors[]` when rendering. Kept here so
// tools that need to enumerate the space (analytics stubs, tests)
// don't have to hit the API for a static piece of metadata.
export const METHOD_FACTORS: Record<
  "CARD" | "DEBIT_ORDER" | "MOBILE_MONEY" | "PAYROLL",
  readonly string[]
> = {
  CARD: [
    "historical_failure_rate",
    "day_of_month_vs_payday",
    "days_since_last_payment",
    "instalment_position",
    "order_value_vs_average",
    "card_health",
    "card_type",
    "debit_order_return_history",
  ],
  DEBIT_ORDER: [
    "historical_failure_rate",
    "day_of_month_vs_payday",
    "days_since_last_payment",
    "instalment_position",
    "order_value_vs_average",
    "card_health",
    "card_type",
    "debit_order_return_history",
  ],
  MOBILE_MONEY: [
    "wallet_balance_trend",
    "historical_failure_rate",
    "time_since_last_inflow",
    "salary_cycle_alignment",
    "concurrent_loan_count",
    "transaction_velocity",
    "airtime_purchase_pattern",
    "loan_cycling_behaviour",
  ],
  PAYROLL: [
    "threshold_headroom",
    "historical_failure_rate",
    "deduction_to_income_ratio",
    "concurrent_loan_count",
    "resubmission_history",
    "borrower_segment",
    "loan_cycling_behaviour",
    "instalment_position",
  ],
} as const;

// Friendly factor display names. Used in the factor breakdown (drawer,
// single-score result, backtest) AND as YAxis labels in the failure-factors
// chart, so keep them under ~28 chars. Preserve semantic direction (e.g.
// "failure rate" not "success rate" — the factor measures the failure side).
export const FACTOR_LABELS: Record<string, string> = {
  historical_failure_rate: "Past failure rate",
  day_of_month_vs_payday: "Date vs payday",
  days_since_last_payment: "Days since last payment",
  instalment_position: "Where in the instalment plan",
  order_value_vs_average: "Amount vs customer typical",
  card_health: "Card health (expiry & declines)",
  card_type: "Card type (debit/credit)",
  debit_order_return_history: "Past debit order returns",
  wallet_balance_trend: "Wallet balance trend",
  time_since_last_inflow: "Time since last wallet inflow",
  salary_cycle_alignment: "Aligned with income timing",
  concurrent_loan_count: "Active loans count",
  transaction_velocity: "Wallet activity change",
  airtime_purchase_pattern: "Airtime buying regularity",
  loan_cycling_behaviour: "Loan stacking pattern",
  // PAYROLL factor set
  threshold_headroom: "Salary threshold headroom",
  deduction_to_income_ratio: "Deduction vs income",
  resubmission_history: "Deduction resubmission history",
  borrower_segment: "Employment sector",
};
