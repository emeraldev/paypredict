/**
 * Plain-English labels for every CSV column / customer_data field.
 *
 * The CSV format uses snake_case (machine-readable, matches the API). The
 * dashboard renders these labels next to or in place of the raw names so a
 * non-technical clerk doesn't have to translate `wallet_balance_7d_avg` to
 * "average wallet balance over the last 7 days".
 *
 * Keep keys in sync with `CustomerData` (api/app/schemas/score.py) and the
 * scoring CSV column list (api/app/services/csv_parser.py).
 */

export interface FieldLabel {
  /** Short label shown in forms / column headers */
  label: string;
  /** One-sentence explanation shown as help text. Optional. */
  help?: string;
}

export const FIELD_LABELS: Record<string, FieldLabel> = {
  // ---- Required collection fields ----
  customer_id: {
    label: "Customer reference",
    help: "Your own customer ID. We never see names or contact info.",
  },
  collection_id: {
    label: "Collection reference",
    help: "Your reference for this specific debit / instalment / payment attempt.",
  },
  collection_amount: {
    label: "Amount",
    help: "How much you're trying to collect.",
  },
  collection_currency: {
    label: "Currency",
  },
  collection_due_date: {
    label: "Due date",
    help: "The day you plan to attempt the collection.",
  },
  collection_method: {
    label: "Collection method",
    help: "How will the money be pulled — card on file, debit order, or mobile money.",
  },

  // ---- Common optional fields ----
  total_payments: {
    label: "Past collection attempts (count)",
    help: "Total number of times you've tried to collect from this customer.",
  },
  successful_payments: {
    label: "Successful past collections (count)",
    help: "How many of those past attempts succeeded.",
  },
  last_successful_payment_date: {
    label: "Date of last successful collection",
  },
  average_collection_amount: {
    label: "Average past collection amount",
    help: "Used to flag when this collection is unusually large vs. typical for the customer.",
  },
  instalment_number: {
    label: "Instalment number",
  },
  total_instalments: {
    label: "Total instalments in this plan",
  },

  // ---- CARD / DEBIT_ORDER optional ----
  card_type: {
    label: "Card type",
    help: "debit or credit (card collections only).",
  },
  card_expiry: {
    label: "Card expiry date",
    help: "Used to flag cards that will be expired by the due date.",
  },
  last_decline_code: {
    label: "Last decline reason",
    help: "What the bank/PSP said last time the collection failed (e.g. insufficient_funds).",
  },
  debit_order_returns: {
    label: "Past debit order returns",
    help: "Pipe-separated list of past return codes (e.g. RD|account_closed).",
  },
  known_salary_day: {
    label: "Customer's payday (1–31)",
    help: "What day of the month the customer typically gets paid.",
  },

  // ---- MOBILE_WALLET optional ----
  wallet_balance_7d_avg: {
    label: "Average wallet balance (last 7 days)",
  },
  wallet_balance_current: {
    label: "Current wallet balance",
  },
  hours_since_last_inflow: {
    label: "Hours since last wallet inflow",
    help: "How long ago money last came into this wallet.",
  },
  regular_inflow_day: {
    label: "Regular pay-in day of the week",
    help: "Lowercase day name — monday, tuesday, etc.",
  },
  active_loan_count: {
    label: "Active loans the customer has",
  },
  transactions_last_7d: {
    label: "Wallet transactions in the last 7 days",
  },
  transactions_avg_7d: {
    label: "Average wallet transactions over 7 days",
  },
  last_airtime_purchase_days_ago: {
    label: "Days since last airtime purchase",
  },
  new_loan_within_repayment_period: {
    label: "Took a new loan during this loan's repayment?",
    help: "true / false — loan cycling is a strong default predictor.",
  },
  loans_taken_last_90d: {
    label: "Loans taken in the last 90 days",
  },
};

export function getFieldLabel(name: string): string {
  return FIELD_LABELS[name]?.label ?? name;
}

export function getFieldHelp(name: string): string | undefined {
  return FIELD_LABELS[name]?.help;
}
