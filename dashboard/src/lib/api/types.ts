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

  // Payroll deduction fields (used when collection_method === "PAYROLL")
  gross_salary?: number | null;
  net_pay?: number | null;
  current_total_deductions?: number | null;
  deduction_threshold_pct?: number | null;
  resubmission_count?: number | null;
  borrower_segment?: string | null;
}

export interface ScoreRequestPayload {
  customer_id: string;
  collection_id: string;
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
  // Populated by the timing optimiser when recommended_action is "shift_date".
  recommended_score: number | null;
  score_improvement: number | null;
  factors: FactorBreakdown[];
  skipped_factors: string[];
  model_version: string;
  scored_at: string;
  scoring_duration_ms: number;
}

// Score list item (table row — lighter than full detail)
export interface ScoreListItem {
  score_id: string;
  customer_id: string;
  collection_id: string;
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
  model_version: string;
  scored_at: string;
}

export interface ScoresSummary {
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  total_value_at_risk: number;
  /** Count of collections where `recommended_action === "shift_date"`. */
  shift_recommended: number;
}

export interface CollectionsListParams {
  page?: number;
  page_size?: number;
  risk_level?: RiskLevel | null;
  collection_method?: CollectionMethod | null;
  /** Filter to rows whose recommended_action matches this value.
   *  Currently used by the dashboard's "N recommend shifting" banner
   *  which sets it to "shift_date" when clicked. */
  recommended_action?: string | null;
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
  outcome_id: string;
  outcome: string;
  failure_reason: string | null;
  attempted_at: string | null;
}

// Chronological loan timeline for the drawer. Each entry represents
// one scored collection for the same customer; `is_current` marks
// the entry the drawer is currently showing so the timeline can
// render "you are here" against the wider journey.
export interface CustomerJourneyEntry {
  score_id: string;
  scored_at: string;
  collection_amount: number;
  collection_currency: Currency;
  collection_method: CollectionMethod;
  collection_due_date: string;
  instalment_number: number | null;
  total_instalments: number | null;
  score: number;
  risk_level: RiskLevel;
  outcome: string | null;
  outcome_reported_at: string | null;
  is_current: boolean;
}

export interface ScoreDetailResponse {
  score_id: string;
  customer_id: string;
  collection_id: string;
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
  recommended_score: number | null;
  score_improvement: number | null;
  factors: FactorBreakdown[];
  skipped_factors: string[];
  model_version: string;
  scored_at: string;
  scoring_duration_ms: number;
  customer_context: CustomerContext;
  outcome: OutcomeSummaryInDetail | null;
  customer_journey: CustomerJourneyEntry[];
}

// ==================== Outcomes ====================

export type OutcomeStatus = "SUCCESS" | "FAILED" | "PENDING";
export type FailureCategory = "SOFT_DECLINE" | "HARD_DECLINE" | "TECHNICAL";

export interface OutcomeListItem {
  outcome_id: string;
  collection_id: string;
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
  search?: string;
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

// Weights are stored per collection method. Each entry in
// `WeightsResponse.methods` is the full factor set for one method the
// tenant actually uses (has scored at least once OR has saved custom
// weights for) — a payroll-only lender receives one entry.
export interface WeightsFactorEntry {
  factor_name: string;
  label: string;
  description: string;
  weight: number;
}

export interface WeightsMethodEntry {
  collection_method: CollectionMethod;
  method_label: string;
  factors: WeightsFactorEntry[];
  total_weight: number;
}

export interface WeightsResponse {
  methods: WeightsMethodEntry[];
}

export interface WeightsUpdateRequest {
  collection_method: CollectionMethod;
  weights: Record<string, number>;
}

// Weight change history — one row per (method, factor) mutation.
// `old_weight` is null when a factor was newly added (first tune or
// "+ Add method" seeding defaults). `new_weight` is null when a factor
// was deleted (stale cleanup during upsert). Both non-null is the
// ordinary update case.
export type WeightChangeActorType = "user" | "api_key" | "system";

export interface WeightChangeLogEntry {
  id: string;
  collection_method: CollectionMethod;
  method_label: string;
  factor_name: string;
  factor_label: string;
  old_weight: number | null;
  new_weight: number | null;
  actor_type: WeightChangeActorType;
  actor_name: string | null;
  context: string | null;
  changed_at: string;
}

export interface WeightChangeLogResponse {
  items: WeightChangeLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

// Activity audit log — generic tenant audit trail covering team,
// API keys, alert config, webhook-secret rotation, and outcome
// soft-deletes. Weight-tuning has its own dedicated audit surface
// (WeightChangeLogEntry above).
export type ActivityActorType = "user" | "api_key" | "system";

export interface ActivityLogEntry {
  id: string;
  entity_type: string;
  entity_id: string | null;
  action: string;
  // `before` and `after` are small dicts of the fields that
  // meaningfully changed. Untyped because the shape varies per
  // entity_type; renderers should be defensive.
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  actor_type: ActivityActorType;
  actor_name: string | null;
  context: string | null;
  created_at: string;
}

export interface ActivityLogResponse {
  items: ActivityLogEntry[];
  total: number;
  limit: number;
  offset: number;
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
  webhook_secret: string;
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

// ==================== Backtest ====================

export interface BacktestRiskBucket {
  count: number;
  actually_failed: number;
  accuracy: number;
}

export interface BacktestSummary {
  overall_accuracy: number;
  collection_rate_actual: number;
  collection_rate_if_acted: number;
  estimated_annual_recovery: number;
  total_failed_value: number;
  flagged_in_advance_value: number;
}

export interface BacktestFactorContribution {
  factor: string;
  avg_score_in_failures: number;
  contribution: number;
}

export interface BacktestConfusionMatrix {
  predicted_high_actual_failed: number;
  predicted_high_actual_success: number;
  predicted_medium_actual_failed: number;
  predicted_medium_actual_success: number;
  predicted_low_actual_failed: number;
  predicted_low_actual_success: number;
}

export interface BacktestResponse {
  backtest_id: string;
  name: string | null;
  total_collections: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  summary: BacktestSummary | null;
  risk_distribution: Record<string, BacktestRiskBucket> | null;
  top_failure_factors: BacktestFactorContribution[] | null;
  confusion_matrix: BacktestConfusionMatrix | null;
  errors?: Array<{ row: number; field: string; message: string }>;
}

export interface BacktestListItem {
  backtest_id: string;
  name: string | null;
  total_collections: number;
  status: string;
  overall_accuracy: number | null;
  created_at: string;
}

export interface BacktestListResponse {
  items: BacktestListItem[];
}

export interface BacktestRequest {
  name?: string;
  collections: Array<{
    customer_id: string;
    collection_id: string;
    collection_amount: number;
    collection_currency: string;
    collection_date: string;
    collection_method: string;
    customer_data?: Record<string, unknown>;
    actual_outcome: string;
    failure_reason?: string | null;
  }>;
}

