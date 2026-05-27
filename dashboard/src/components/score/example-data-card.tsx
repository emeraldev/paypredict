"use client";

import { ChevronDownIcon, ChevronRightIcon } from "lucide-react";
import { useState } from "react";
import { MethodBadge } from "@/components/shared/method-badge";
import { RiskBadge } from "@/components/shared/risk-badge";
import { Card, CardContent } from "@/components/ui/card";
import { getFieldLabel } from "@/lib/utils/field-labels";

interface ExampleRow {
  title: string;
  expectedRisk: "LOW" | "MEDIUM" | "HIGH";
  method: "CARD" | "DEBIT_ORDER" | "MOBILE_MONEY";
  rationale: string;
  fields: Record<string, string>;
}

// Reference rows tuned to exercise every factor on each factor set.
// These are display-only — never sent to the upload endpoint.
const EXAMPLES: ExampleRow[] = [
  {
    title: "Card on payday, healthy history",
    expectedRisk: "LOW",
    method: "CARD",
    rationale:
      "Debit card with strong past success rate, due date aligned with the customer's payday, card not expiring soon.",
    fields: {
      customer_id: "EXAMPLE_001",
      collection_id: "EXAMPLE_INST_201",
      collection_amount: "833.33",
      collection_currency: "ZAR",
      collection_due_date: "2026-07-25",
      collection_method: "CARD",
      total_payments: "8",
      successful_payments: "7",
      last_successful_payment_date: "2026-06-25",
      average_collection_amount: "800.00",
      instalment_number: "3",
      total_instalments: "6",
      card_type: "debit",
      card_expiry: "2028-09-01",
      known_salary_day: "25",
    },
  },
  {
    title: "First instalment, off-payday, credit card expiring",
    expectedRisk: "HIGH",
    method: "CARD",
    rationale:
      "New customer (no history), large amount vs. typical, due date 22 days before payday, credit card expiring next month, recent insufficient-funds decline.",
    fields: {
      customer_id: "EXAMPLE_002",
      collection_id: "EXAMPLE_INST_202",
      collection_amount: "2500.00",
      collection_currency: "ZAR",
      collection_due_date: "2026-07-03",
      collection_method: "CARD",
      total_payments: "0",
      successful_payments: "0",
      instalment_number: "1",
      total_instalments: "6",
      card_type: "credit",
      card_expiry: "2026-08-15",
      last_decline_code: "insufficient_funds",
      known_salary_day: "25",
    },
  },
  {
    title: "Debit order with one prior return",
    expectedRisk: "MEDIUM",
    method: "DEBIT_ORDER",
    rationale:
      "Modest success rate, amount slightly above average, due a few days before payday, one return on file.",
    fields: {
      customer_id: "EXAMPLE_003",
      collection_id: "EXAMPLE_INST_203",
      collection_amount: "1200.00",
      collection_currency: "ZAR",
      collection_due_date: "2026-07-22",
      collection_method: "DEBIT_ORDER",
      total_payments: "10",
      successful_payments: "7",
      last_successful_payment_date: "2026-06-22",
      average_collection_amount: "1000.00",
      instalment_number: "2",
      total_instalments: "4",
      debit_order_returns: "insufficient_funds",
      known_salary_day: "25",
    },
  },
  {
    title: "Wallet topped up recently, on inflow day",
    expectedRisk: "LOW",
    method: "MOBILE_MONEY",
    rationale:
      "Wallet balance covers collection ~2x, recent inflow within the day, due date matches the typical inflow day, single active loan.",
    fields: {
      customer_id: "EXAMPLE_ZM1",
      collection_id: "EXAMPLE_INST_501",
      collection_amount: "250.00",
      collection_currency: "ZMW",
      collection_due_date: "2026-07-25",
      collection_method: "MOBILE_MONEY",
      total_payments: "5",
      successful_payments: "5",
      instalment_number: "3",
      total_instalments: "6",
      wallet_balance_7d_avg: "500.00",
      wallet_balance_current: "480.00",
      hours_since_last_inflow: "12",
      regular_inflow_day: "friday",
      active_loan_count: "1",
      transactions_last_7d: "14",
      transactions_avg_7d: "12",
      last_airtime_purchase_days_ago: "2",
      new_loan_within_repayment_period: "false",
      loans_taken_last_90d: "1",
    },
  },
  {
    title: "Empty wallet, no recent inflow, loan cycling",
    expectedRisk: "HIGH",
    method: "MOBILE_MONEY",
    rationale:
      "Current balance far below collection amount, no inflow for ~6 days, sharp drop in transaction activity, multiple active loans, new loan taken inside the repayment period.",
    fields: {
      customer_id: "EXAMPLE_ZM2",
      collection_id: "EXAMPLE_INST_502",
      collection_amount: "800.00",
      collection_currency: "ZMW",
      collection_due_date: "2026-07-15",
      collection_method: "MOBILE_MONEY",
      total_payments: "3",
      successful_payments: "0",
      instalment_number: "1",
      total_instalments: "6",
      wallet_balance_7d_avg: "50.00",
      wallet_balance_current: "5.00",
      hours_since_last_inflow: "144",
      regular_inflow_day: "friday",
      active_loan_count: "4",
      transactions_last_7d: "2",
      transactions_avg_7d: "15",
      last_airtime_purchase_days_ago: "30",
      new_loan_within_repayment_period: "true",
      loans_taken_last_90d: "5",
    },
  },
  {
    title: "Declining wallet, partial alignment",
    expectedRisk: "MEDIUM",
    method: "MOBILE_MONEY",
    rationale:
      "Balance trending down but covers the collection, inflow ~36h ago, two active loans, mild drop in activity.",
    fields: {
      customer_id: "EXAMPLE_ZM3",
      collection_id: "EXAMPLE_INST_503",
      collection_amount: "350.00",
      collection_currency: "ZMW",
      collection_due_date: "2026-07-20",
      collection_method: "MOBILE_MONEY",
      total_payments: "6",
      successful_payments: "4",
      instalment_number: "4",
      total_instalments: "6",
      wallet_balance_7d_avg: "400.00",
      wallet_balance_current: "280.00",
      hours_since_last_inflow: "36",
      regular_inflow_day: "wednesday",
      active_loan_count: "2",
      transactions_last_7d: "9",
      transactions_avg_7d: "11",
      last_airtime_purchase_days_ago: "10",
      new_loan_within_repayment_period: "false",
      loans_taken_last_90d: "2",
    },
  },
];

export function ExampleDataCard() {
  const [open, setOpen] = useState(false);

  return (
    <Card>
      <CardContent className="p-0">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between gap-3 px-6 py-4 text-left transition-colors hover:bg-accent/40"
        >
          <div>
            <p className="text-sm font-medium text-foreground">
              Example data — what realistic values look like
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Six reference rows that exercise each factor across both factor
              sets. Display-only — these are not uploaded.
            </p>
          </div>
          {open ? (
            <ChevronDownIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRightIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
        </button>

        {open && (
          <div className="grid grid-cols-1 gap-3 border-t border-border bg-muted/20 p-4 lg:grid-cols-2">
            {EXAMPLES.map((ex) => (
              <div
                key={ex.fields.customer_id}
                className="rounded-md border border-border bg-card p-4"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <RiskBadge level={ex.expectedRisk} className="text-[10px]" />
                  <MethodBadge method={ex.method} />
                  <span className="text-sm font-medium text-foreground">
                    {ex.title}
                  </span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  {ex.rationale}
                </p>
                <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-0.5 text-xs">
                  {Object.entries(ex.fields).map(([key, value]) => (
                    <FieldRow key={key} name={key} value={value} />
                  ))}
                </dl>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function FieldRow({ name, value }: { name: string; value: string }) {
  return (
    <>
      <dt className="text-muted-foreground">
        {getFieldLabel(name)}
        <span className="ml-1 font-mono text-[10px] text-muted-foreground/60">
          ({name})
        </span>
      </dt>
      <dd className="font-mono text-foreground">{value}</dd>
    </>
  );
}
