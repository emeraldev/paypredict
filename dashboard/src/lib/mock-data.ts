// MOCK DATA — single source of truth for all dashboard mocks.
// Replace with real API calls in Step 8.

import type {
  AlertSettings,
  AnalyticsSummary,
  ApiKey,
  Collection,
  CollectionRatePoint,
  FactorContribution,
  Outcome,
  Tenant,
  TeamMember,
  WeightsResponse,
} from "@/lib/api/types";

// ==================== Tenant ====================

export const mockTenant: Tenant = {
  id: "tenant_001",
  name: "Demo BNPL SA",
  market: "SA",
  factor_set: "CARD_DEBIT",
  plan: "STARTER",
  alert_threshold: 0.2,
};

// ==================== Collections (25) ====================

const factorTemplates = {
  card: [
    { factor: "historical_failure_rate", weight: 0.25 },
    { factor: "day_of_month_vs_payday", weight: 0.2 },
    { factor: "days_since_last_payment", weight: 0.15 },
    { factor: "instalment_position", weight: 0.1 },
    { factor: "order_value_vs_average", weight: 0.1 },
    { factor: "card_health", weight: 0.1 },
    { factor: "card_type", weight: 0.1 },
  ],
  debit: [
    { factor: "historical_failure_rate", weight: 0.27 },
    { factor: "day_of_month_vs_payday", weight: 0.21 },
    { factor: "days_since_last_payment", weight: 0.16 },
    { factor: "instalment_position", weight: 0.11 },
    { factor: "order_value_vs_average", weight: 0.11 },
    { factor: "debit_order_return_history", weight: 0.14 },
  ],
  wallet: [
    { factor: "wallet_balance_trend", weight: 0.25 },
    { factor: "historical_failure_rate", weight: 0.2 },
    { factor: "time_since_last_inflow", weight: 0.15 },
    { factor: "salary_cycle_alignment", weight: 0.15 },
    { factor: "concurrent_loan_count", weight: 0.1 },
    { factor: "transaction_velocity", weight: 0.05 },
    { factor: "airtime_purchase_pattern", weight: 0.05 },
    { factor: "loan_cycling_behaviour", weight: 0.05 },
  ],
};

function buildFactors(
  template: { factor: string; weight: number }[],
  rawScores: number[],
) {
  return template.map((t, i) => {
    const raw = rawScores[i] ?? 0.3;
    return {
      factor: t.factor,
      raw_score: raw,
      weight: t.weight,
      weighted_score: Number((raw * t.weight).toFixed(4)),
      explanation: `Mock explanation for ${t.factor}`,
    };
  });
}

interface MockCollectionInput {
  id: number;
  customer: string;
  amount: number;
  currency: "ZAR" | "ZMW";
  dueDays: number; // days from today (negative = overdue)
  method: "CARD" | "DEBIT_ORDER" | "MOBILE_MONEY";
  rawScores: number[];
}

const mockInputs: MockCollectionInput[] = [
  { id: 1, customer: "cust_001", amount: 1500, currency: "ZAR", dueDays: -1, method: "CARD",
    rawScores: [0.8, 0.9, 0.7, 0.6, 0.4, 0.7, 0.5] },
  { id: 2, customer: "cust_002", amount: 850, currency: "ZAR", dueDays: 0, method: "DEBIT_ORDER",
    rawScores: [0.9, 0.8, 0.6, 0.7, 0.5, 0.9] },
  { id: 3, customer: "cust_003", amount: 2400, currency: "ZAR", dueDays: 1, method: "CARD",
    rawScores: [0.5, 0.6, 0.4, 0.5, 0.7, 0.4, 0.5] },
  { id: 4, customer: "cust_004", amount: 320, currency: "ZMW", dueDays: 2, method: "MOBILE_MONEY",
    rawScores: [0.85, 0.7, 0.6, 0.5, 0.3, 0.4, 0.3, 0.2] },
  { id: 5, customer: "cust_005", amount: 1200, currency: "ZAR", dueDays: 3, method: "CARD",
    rawScores: [0.2, 0.3, 0.1, 0.2, 0.1, 0.2, 0.2] },
  { id: 6, customer: "cust_006", amount: 4500, currency: "ZAR", dueDays: 4, method: "DEBIT_ORDER",
    rawScores: [0.4, 0.5, 0.3, 0.4, 0.3, 0.2] },
  { id: 7, customer: "cust_007", amount: 180, currency: "ZMW", dueDays: 5, method: "MOBILE_MONEY",
    rawScores: [0.3, 0.2, 0.2, 0.1, 0.0, 0.1, 0.1, 0.1] },
  { id: 8, customer: "cust_008", amount: 2750, currency: "ZAR", dueDays: 6, method: "CARD",
    rawScores: [0.6, 0.5, 0.4, 0.3, 0.5, 0.6, 0.4] },
  { id: 9, customer: "cust_009", amount: 950, currency: "ZAR", dueDays: 7, method: "CARD",
    rawScores: [0.1, 0.2, 0.1, 0.1, 0.2, 0.1, 0.2] },
  { id: 10, customer: "cust_010", amount: 540, currency: "ZMW", dueDays: 8, method: "MOBILE_MONEY",
    rawScores: [0.6, 0.5, 0.4, 0.3, 0.5, 0.3, 0.2, 0.2] },
  { id: 11, customer: "cust_011", amount: 3200, currency: "ZAR", dueDays: 9, method: "DEBIT_ORDER",
    rawScores: [0.85, 0.7, 0.6, 0.5, 0.5, 0.7] },
  { id: 12, customer: "cust_012", amount: 670, currency: "ZAR", dueDays: 10, method: "CARD",
    rawScores: [0.3, 0.4, 0.2, 0.3, 0.4, 0.3, 0.2] },
  { id: 13, customer: "cust_013", amount: 220, currency: "ZMW", dueDays: 11, method: "MOBILE_MONEY",
    rawScores: [0.2, 0.3, 0.1, 0.2, 0.0, 0.1, 0.1, 0.1] },
  { id: 14, customer: "cust_014", amount: 5800, currency: "ZAR", dueDays: 12, method: "DEBIT_ORDER",
    rawScores: [0.5, 0.4, 0.5, 0.6, 0.4, 0.5] },
  { id: 15, customer: "cust_015", amount: 1100, currency: "ZAR", dueDays: 13, method: "CARD",
    rawScores: [0.7, 0.8, 0.6, 0.5, 0.6, 0.5, 0.5] },
  { id: 16, customer: "cust_016", amount: 410, currency: "ZMW", dueDays: 14, method: "MOBILE_MONEY",
    rawScores: [0.7, 0.6, 0.5, 0.4, 0.6, 0.4, 0.3, 0.4] },
  { id: 17, customer: "cust_017", amount: 1850, currency: "ZAR", dueDays: 15, method: "CARD",
    rawScores: [0.2, 0.3, 0.1, 0.2, 0.2, 0.1, 0.2] },
  { id: 18, customer: "cust_018", amount: 980, currency: "ZAR", dueDays: 16, method: "DEBIT_ORDER",
    rawScores: [0.4, 0.5, 0.3, 0.3, 0.4, 0.2] },
  { id: 19, customer: "cust_019", amount: 290, currency: "ZMW", dueDays: 17, method: "MOBILE_MONEY",
    rawScores: [0.4, 0.4, 0.3, 0.2, 0.3, 0.2, 0.2, 0.2] },
  { id: 20, customer: "cust_020", amount: 6200, currency: "ZAR", dueDays: 18, method: "CARD",
    rawScores: [0.6, 0.5, 0.5, 0.6, 0.7, 0.5, 0.4] },
  { id: 21, customer: "cust_021", amount: 1450, currency: "ZAR", dueDays: 19, method: "CARD",
    rawScores: [0.3, 0.2, 0.2, 0.3, 0.2, 0.2, 0.2] },
  { id: 22, customer: "cust_022", amount: 730, currency: "ZAR", dueDays: 20, method: "DEBIT_ORDER",
    rawScores: [0.6, 0.5, 0.4, 0.3, 0.4, 0.3] },
  { id: 23, customer: "cust_023", amount: 380, currency: "ZMW", dueDays: 21, method: "MOBILE_MONEY",
    rawScores: [0.1, 0.2, 0.1, 0.1, 0.0, 0.1, 0.1, 0.1] },
  { id: 24, customer: "cust_024", amount: 2100, currency: "ZAR", dueDays: 22, method: "CARD",
    rawScores: [0.5, 0.4, 0.4, 0.3, 0.3, 0.4, 0.3] },
  { id: 25, customer: "cust_025", amount: 870, currency: "ZAR", dueDays: 23, method: "DEBIT_ORDER",
    rawScores: [0.3, 0.4, 0.3, 0.2, 0.3, 0.2] },
];

function daysFromToday(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().split("T")[0];
}

function isoNow(offsetHours = 0): string {
  const d = new Date();
  d.setHours(d.getHours() - offsetHours);
  return d.toISOString();
}

function computeScore(rawScores: number[], weights: number[]): number {
  let total = 0;
  for (let i = 0; i < rawScores.length; i++) {
    total += rawScores[i] * weights[i];
  }
  return Number(total.toFixed(4));
}

function riskLevel(score: number): "HIGH" | "MEDIUM" | "LOW" {
  if (score > 0.6) return "HIGH";
  if (score > 0.3) return "MEDIUM";
  return "LOW";
}

function recommendedAction(level: "HIGH" | "MEDIUM" | "LOW"): string {
  if (level === "HIGH") return "flag_for_review";
  if (level === "MEDIUM") return "pre_collection_sms";
  return "collect_normally";
}

export const mockCollections: Collection[] = mockInputs.map((input) => {
  const template =
    input.method === "CARD"
      ? factorTemplates.card
      : input.method === "DEBIT_ORDER"
        ? factorTemplates.debit
        : factorTemplates.wallet;

  const factors = buildFactors(template, input.rawScores);
  const score = computeScore(
    input.rawScores,
    template.map((t) => t.weight),
  );
  const level = riskLevel(score);
  const modelVersion =
    input.method === "MOBILE_MONEY" ? "heuristic_wallet_v1" : "heuristic_card_v1";

  const skipped: string[] =
    input.method === "CARD"
      ? ["debit_order_return_history"]
      : input.method === "DEBIT_ORDER"
        ? ["card_health", "card_type"]
        : [];

  return {
    score_id: `sr_${String(input.id).padStart(4, "0")}`,
    external_customer_id: input.customer,
    external_collection_id: `col_${String(input.id).padStart(4, "0")}`,
    collection_amount: input.amount,
    collection_currency: input.currency,
    collection_due_date: daysFromToday(input.dueDays),
    collection_method: input.method,
    score,
    risk_level: level,
    recommended_action: recommendedAction(level),
    recommended_collection_date: level === "HIGH" ? daysFromToday(input.dueDays + 5) : null,
    factors,
    skipped_factors: skipped,
    model_version: modelVersion,
    scored_at: isoNow(input.id * 2),
    customer_data: {
      total_payments: 8 + (input.id % 5),
      successful_payments: 5 + (input.id % 4),
      last_successful_payment_date: daysFromToday(-15 - (input.id % 30)),
      average_collection_amount: input.amount * (0.8 + (input.id % 5) * 0.1),
      instalment_number: 2 + (input.id % 6),
      total_instalments: 6,
      ...(input.method !== "MOBILE_MONEY" && {
        card_type: input.id % 2 === 0 ? "debit" : "credit",
        card_expiry_date: daysFromToday(180 + (input.id % 365)),
      }),
      ...(input.method === "MOBILE_MONEY" && {
        wallet_balance_7d_avg: input.amount * 1.5,
        wallet_balance_current: input.amount * (input.rawScores[0] < 0.5 ? 1.8 : 0.6),
        hours_since_last_inflow: 6 + input.id * 3,
        active_loan_count: input.id % 3,
      }),
    },
  };
});

// ==================== Outcomes (20) ====================

export const mockOutcomes: Outcome[] = Array.from({ length: 20 }, (_, i) => {
  const collection = mockCollections[i % mockCollections.length];
  // Match prediction 70% of the time
  const matchesPrediction = i % 10 < 7;
  const predicted = collection.risk_level;
  const outcome: "SUCCESS" | "FAILED" | "PENDING" =
    i % 11 === 0
      ? "PENDING"
      : matchesPrediction
        ? predicted === "HIGH"
          ? "FAILED"
          : "SUCCESS"
        : predicted === "HIGH"
          ? "SUCCESS"
          : "FAILED";

  const failureReasons = ["insufficient_funds", "card_expired", "wallet_empty", "do_not_honour"];

  return {
    outcome_id: `out_${String(i + 1).padStart(4, "0")}`,
    score_id: collection.score_id,
    external_collection_id: collection.external_collection_id,
    outcome,
    failure_reason: outcome === "FAILED" ? failureReasons[i % failureReasons.length] : null,
    failure_category: outcome === "FAILED" ? "SOFT_DECLINE" : null,
    amount_collected: outcome === "SUCCESS" ? collection.collection_amount : null,
    attempted_at: isoNow(i * 5),
    reported_at: isoNow(i * 5 - 1),
    predicted_risk_level: predicted,
    predicted_score: collection.score,
    collection_method: collection.collection_method,
    collection_amount: collection.collection_amount,
    collection_currency: collection.collection_currency,
  };
});

// ==================== Analytics ====================

export const mockAnalyticsSummary: AnalyticsSummary = {
  period: "30d",
  total_scored: 4521,
  total_outcomes_reported: 3890,
  collection_rate: 0.78,
  risk_distribution: {
    high: 312,
    medium: 1205,
    low: 3004,
  },
  prediction_accuracy: {
    high_risk_actually_failed: 0.82,
    low_risk_actually_succeeded: 0.94,
  },
  value_at_risk: 156000,
  value_recovered_vs_baseline: 23400,
};

export const mockCollectionRate: CollectionRatePoint[] = Array.from({ length: 30 }, (_, i) => {
  const date = new Date();
  date.setDate(date.getDate() - (29 - i));
  const total = 120 + Math.round(Math.sin(i * 0.5) * 20 + Math.random() * 15);
  const successful = Math.round(total * (0.72 + Math.sin(i * 0.3) * 0.08));
  return {
    date: date.toISOString().split("T")[0],
    rate: Number((successful / total).toFixed(3)),
    total,
    successful,
  };
});

export const mockFactorContributions: FactorContribution[] = [
  { factor: "historical_failure_rate", contribution: 0.28, description: "Past payment failure ratio" },
  { factor: "card_health", contribution: 0.18, description: "Card expiry and decline history" },
  { factor: "wallet_balance_trend", contribution: 0.14, description: "Declining wallet balance" },
  { factor: "day_of_month_vs_payday", contribution: 0.12, description: "Pre-payday timing" },
  { factor: "debit_order_return_history", contribution: 0.1, description: "Recent debit returns" },
  { factor: "instalment_position", contribution: 0.08, description: "Late-stage instalment fatigue" },
  { factor: "concurrent_loan_count", contribution: 0.06, description: "Multiple active loans" },
  { factor: "loan_cycling_behaviour", contribution: 0.04, description: "Loan refinancing pattern" },
];

// ==================== Settings ====================

export const mockWeights: WeightsResponse = {
  factor_set: "CARD_DEBIT",
  weights: [
    { factor_name: "historical_failure_rate", weight: 0.25 },
    { factor_name: "day_of_month_vs_payday", weight: 0.2 },
    { factor_name: "days_since_last_payment", weight: 0.15 },
    { factor_name: "instalment_position", weight: 0.1 },
    { factor_name: "order_value_vs_average", weight: 0.1 },
    { factor_name: "card_health", weight: 0.1 },
    { factor_name: "card_type", weight: 0.05 },
    { factor_name: "debit_order_return_history", weight: 0.05 },
  ],
};

export const mockApiKeys: ApiKey[] = [
  {
    id: "key_001",
    label: "Production",
    key_prefix: "pk_live_",
    is_active: true,
    last_used_at: isoNow(2),
    created_at: isoNow(24 * 60),
  },
  {
    id: "key_002",
    label: "Test / Sandbox",
    key_prefix: "pk_test_",
    is_active: true,
    last_used_at: isoNow(48),
    created_at: isoNow(24 * 90),
  },
];

export const mockTeamMembers: TeamMember[] = [
  {
    id: "user_001",
    email: "admin@demo-sa.paypredict.dev",
    name: "Sarah Admin",
    role: "ADMIN",
    last_login_at: isoNow(1),
  },
  {
    id: "user_002",
    email: "ops@demo-sa.paypredict.dev",
    name: "Mike Ops",
    role: "MANAGER",
    last_login_at: isoNow(8),
  },
  {
    id: "user_003",
    email: "viewer@demo-sa.paypredict.dev",
    name: "Jess Viewer",
    role: "VIEWER",
    last_login_at: isoNow(72),
  },
];

export const mockAlertSettings: AlertSettings = {
  alert_threshold: 0.2,
  webhook_url: null,
  slack_webhook_url: null,
};
