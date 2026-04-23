// API types — must match Pydantic schemas in api/app/schemas/

import type { Currency } from "@/lib/utils/format-currency";
import type { CollectionMethod } from "@/lib/utils/format-method";
import type { RiskLevel } from "@/lib/utils/format-risk";

// ==================== Score / Collection ====================

export interface CustomerData {
  total_payments?: number;
  successful_payments?: number;
  last_successful_payment_date?: string | null;
  average_collection_amount?: number | null;
  instalment_number?: number | null;
  total_instalments?: number | null;

  // SA card fields
  card_type?: "credit" | "debit" | null;
  card_expiry_date?: string | null;
  last_decline_code?: string | null;
  debit_order_returns?: string[];
  known_salary_day?: number | null;

  // ZM mobile money fields
  wallet_balance_7d_avg?: number | null;
  wallet_balance_current?: number | null;
  hours_since_last_inflow?: number | null;
  regular_inflow_day?: string | null;
  active_loan_count?: number | null;
  transactions_last_7d?: number | null;
  transactions_avg_7d?: number | null;
  last_airtime_purchase_days_ago?: number | null;
  new_loan_within_repayment_period?: boolean | null;
  loans_taken_last_90d?: number | null;
}

export interface ScoreRequestPayload {
  external_customer_id: string;
  external_collection_id: string;
  collection_amount: number;
  collection_currency: Currency;
  collection_due_date: string;
  collection_method: CollectionMethod;
  customer_data: CustomerData;
}

export interface FactorBreakdown {
  factor: string;
  raw_score: number;
  weight: number;
  weighted_score: number;
  explanation: string;
}

export interface ScoreResponse {
  score_id: string;
  score: number; // 0.0 - 1.0
  risk_level: RiskLevel;
  recommended_action: string;
  recommended_collection_date: string | null;
  factors: FactorBreakdown[];
  skipped_factors: string[];
  model_version: string;
  scored_at: string;
  scoring_duration_ms: number;
}

// Collection record (extends ScoreResponse with the request context)
export interface Collection {
  score_id: string;
  external_customer_id: string;
  external_collection_id: string;
  collection_amount: number;
  collection_currency: Currency;
  collection_due_date: string;
  collection_method: CollectionMethod;
  score: number;
  risk_level: RiskLevel;
  recommended_action: string;
  recommended_collection_date: string | null;
  factors: FactorBreakdown[];
  skipped_factors: string[];
  model_version: string;
  scored_at: string;
  customer_data: CustomerData;
}

export interface CollectionsListParams {
  page?: number;
  page_size?: number;
  risk_level?: RiskLevel | null;
  collection_method?: CollectionMethod | null;
  search?: string;
  date_from?: string;
  date_to?: string;
}

export interface CollectionsListResponse {
  items: Collection[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ==================== Outcomes ====================

export type OutcomeStatus = "SUCCESS" | "FAILED" | "PENDING";
export type FailureCategory = "SOFT_DECLINE" | "HARD_DECLINE" | "TECHNICAL";

export interface Outcome {
  outcome_id: string;
  score_id: string | null;
  external_collection_id: string;
  outcome: OutcomeStatus;
  failure_reason: string | null;
  failure_category: FailureCategory | null;
  amount_collected: number | null;
  attempted_at: string;
  reported_at: string;
  // Joined for table display
  predicted_risk_level?: RiskLevel | null;
  predicted_score?: number | null;
  collection_method?: CollectionMethod | null;
  collection_amount?: number | null;
  collection_currency?: Currency | null;
}

export type OutcomeFilter = "ALL" | "MATCHED" | "MISMATCHED" | "PENDING";

export interface OutcomesListParams {
  page?: number;
  page_size?: number;
  filter?: OutcomeFilter;
}

export interface OutcomesListResponse {
  items: Outcome[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  stats: OutcomeStats;
}

export interface OutcomeStats {
  total_reported: number;
  collection_rate: number;
  matched: number;
  mismatched: number;
  pending: number;
}

// ==================== Analytics ====================

export interface AnalyticsSummary {
  period: string;
  total_scored: number;
  total_outcomes_reported: number;
  collection_rate: number;
  risk_distribution: {
    high: number;
    medium: number;
    low: number;
  };
  prediction_accuracy: {
    high_risk_actually_failed: number;
    low_risk_actually_succeeded: number;
  };
  value_at_risk: number;
  value_recovered_vs_baseline: number;
}

export interface CollectionRatePoint {
  date: string;
  rate: number;
  total: number;
  successful: number;
}

export interface FactorContribution {
  factor: string;
  contribution: number;
  description: string;
}

// ==================== Config ====================

export interface FactorWeight {
  factor_name: string;
  weight: number;
}

export interface WeightsResponse {
  factor_set: "CARD_DEBIT" | "MOBILE_WALLET" | "CUSTOM";
  weights: FactorWeight[];
}

export interface ApiKey {
  id: string;
  label: string;
  key_prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface TeamMember {
  id: string;
  email: string;
  name: string;
  role: "ADMIN" | "MANAGER" | "VIEWER";
  last_login_at: string | null;
}

export interface AlertSettings {
  alert_threshold: number;
  webhook_url: string | null;
  slack_webhook_url: string | null;
}

// ==================== Tenant ====================

export interface Tenant {
  id: string;
  name: string;
  market: "SA" | "ZM";
  factor_set: "CARD_DEBIT" | "MOBILE_WALLET" | "CUSTOM";
  plan: "PILOT" | "STARTER" | "GROWTH" | "SCALE";
  alert_threshold: number;
}

// ==================== Errors ====================

export interface ApiErrorBody {
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  detail?: string;
}
