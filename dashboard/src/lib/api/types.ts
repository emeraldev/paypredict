// API types — must match Pydantic schemas in api/app/schemas/

import type { Currency } from "@/lib/utils/format-currency";
import type { CollectionMethod } from "@/lib/utils/format-method";
import type { RiskLevel } from "@/lib/utils/format-risk";

// ==================== Auth ====================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TenantSummary {
  id: string;
  name: string;
  market: "SA" | "ZM";
  factor_set: "CARD_DEBIT" | "MOBILE_WALLET" | "CUSTOM";
  plan: "PILOT" | "STARTER" | "GROWTH" | "SCALE";
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  role: "ADMIN" | "MANAGER" | "VIEWER";
  last_login_at: string | null;
  tenant: TenantSummary;
}

export interface LoginResponse {
  token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

// ==================== Pagination ====================

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

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

// Score list item (table row — lighter than full detail)
export interface ScoreListItem {
  score_id: string;
  external_customer_id: string;
  external_collection_id: string;
  collection_amount: number;
  collection_currency: Currency;
  collection_due_date: string;
  collection_method: CollectionMethod;
  instalment_number: number | null;
  total_instalments: number | null;
  score: number;
  risk_level: RiskLevel;
  recommended_action: string;
  model_version: string;
  scored_at: string;
}

export interface ScoresSummary {
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  total_value_at_risk: number;
}

export interface CollectionsListParams {
  page?: number;
  page_size?: number;
  risk_level?: RiskLevel | null;
  collection_method?: CollectionMethod | null;
  search?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface CollectionsListResponse {
  items: ScoreListItem[];
  pagination: PaginationMeta;
  summary: ScoresSummary;
}

// Score detail (drawer — full breakdown)
export interface CustomerContext {
  total_payments: number | null;
  successful_payments: number | null;
  success_rate: number | null;
  days_since_last_payment: number | null;
}

export interface OutcomeSummaryInDetail {
  outcome: string;
  failure_reason: string | null;
  attempted_at: string | null;
}

export interface ScoreDetailResponse {
  score_id: string;
  external_customer_id: string;
  external_collection_id: string;
  collection_amount: number;
  collection_currency: Currency;
  collection_due_date: string;
  collection_method: CollectionMethod;
  instalment_number: number | null;
  total_instalments: number | null;
  score: number;
  risk_level: RiskLevel;
  recommended_action: string;
  recommended_collection_date: string | null;
  factors: FactorBreakdown[];
  skipped_factors: string[];
  model_version: string;
  scored_at: string;
  scoring_duration_ms: number;
  customer_context: CustomerContext;
  outcome: OutcomeSummaryInDetail | null;
}

// ==================== Outcomes ====================

export type OutcomeStatus = "SUCCESS" | "FAILED" | "PENDING";
export type FailureCategory = "SOFT_DECLINE" | "HARD_DECLINE" | "TECHNICAL";

export interface OutcomeListItem {
  outcome_id: string;
  external_collection_id: string;
  score: number | null;
  risk_level: RiskLevel | null;
  outcome: OutcomeStatus;
  failure_reason: string | null;
  collection_amount: number | null;
  collection_currency: Currency | null;
  collection_method: CollectionMethod | null;
  attempted_at: string;
  reported_at: string;
  prediction_matched: boolean | null;
}

export type OutcomeFilter = "ALL" | "MATCHED" | "MISMATCHED";

export interface OutcomesListParams {
  page?: number;
  page_size?: number;
  outcome?: "SUCCESS" | "FAILED";
  match?: "MATCHED" | "MISMATCHED";
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface OutcomeListStats {
  total_outcomes: number;
  success_count: number;
  failed_count: number;
  success_rate: number;
  predictions_matched: number;
  match_rate: number;
}

export interface OutcomesListResponse {
  items: OutcomeListItem[];
  pagination: PaginationMeta;
  stats: OutcomeListStats;
}

// ==================== Analytics ====================

export interface PredictionAccuracy {
  high_risk_failure_rate: number;
  low_risk_success_rate: number;
  overall_accuracy: number;
}

export interface RiskDistribution {
  high: number;
  medium: number;
  low: number;
}

export interface AnalyticsSummary {
  period: string;
  total_scored: number;
  total_outcomes: number;
  collection_rate: number;
  collection_rate_change: number;
  risk_distribution: RiskDistribution;
  prediction_accuracy: PredictionAccuracy;
  total_value_scored: number;
  total_value_at_risk: number;
  avg_score: number;
  outcomes_reporting_rate: number;
}

export interface CollectionRatePoint {
  date: string;
  collection_rate: number;
  scored_count: number;
  failed_count: number;
}

export interface FactorContribution {
  factor: string;
  avg_contribution: number;
  correlation_with_failure: number;
}

export interface CollectionRateResponse {
  data_points: CollectionRatePoint[];
}

export interface FactorsResponse {
  factors: FactorContribution[];
}

export interface ConfusionMatrix {
  predicted_high_actual_failed: number;
  predicted_high_actual_success: number;
  predicted_medium_actual_failed: number;
  predicted_medium_actual_success: number;
  predicted_low_actual_failed: number;
  predicted_low_actual_success: number;
}

export interface AccuracyResponse {
  confusion_matrix: ConfusionMatrix;
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

export interface ApiKeyListItem {
  id: string;
  prefix: string;
  label: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiKeyCreateResponse {
  id: string;
  key: string;
  prefix: string;
  label: string;
  message: string;
}

export interface ApiKeyListResponse {
  items: ApiKeyListItem[];
}

export interface TeamMember {
  id: string;
  email: string;
  name: string;
  role: "ADMIN" | "MANAGER" | "VIEWER";
  last_login_at: string | null;
  created_at: string;
}

export interface TeamListResponse {
  items: TeamMember[];
}

export interface AlertSettings {
  high_risk_threshold: number;
  webhook_url: string | null;
  slack_webhook_url: string | null;
  email_digest: "OFF" | "DAILY" | "WEEKLY";
  email_recipients: string[];
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
