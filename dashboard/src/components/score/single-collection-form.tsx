"use client";

import { ChevronDownIcon, ChevronRightIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { scoresApi } from "@/lib/api/scores";
import { getFieldHelp, getFieldLabel } from "@/lib/utils/field-labels";
import type {
  CustomerData,
  ScoreRequestPayload,
  ScoreResponse,
} from "@/lib/api/types";

type Method = "CARD" | "DEBIT_ORDER" | "MOBILE_MONEY";

interface SingleCollectionFormProps {
  onScored: (result: ScoreResponse) => void;
}

const DAY_OF_WEEK_OPTIONS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

export function SingleCollectionForm({ onScored }: SingleCollectionFormProps) {
  // Required fields
  const [customerId, setCustomerId] = useState("");
  const [collectionId, setCollectionId] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState<"ZAR" | "ZMW">("ZAR");
  const [dueDate, setDueDate] = useState("");
  const [method, setMethod] = useState<Method>("CARD");

  // Common optional fields
  const [optionalOpen, setOptionalOpen] = useState(false);
  const [totalPayments, setTotalPayments] = useState("");
  const [successfulPayments, setSuccessfulPayments] = useState("");
  const [lastSuccessfulPaymentDate, setLastSuccessfulPaymentDate] = useState("");
  const [averageCollectionAmount, setAverageCollectionAmount] = useState("");
  const [instalmentNumber, setInstalmentNumber] = useState("");
  const [totalInstalments, setTotalInstalments] = useState("");

  // Card / debit-order optional
  const [cardType, setCardType] = useState<"" | "debit" | "credit">("");
  const [cardExpiryDate, setCardExpiryDate] = useState("");
  const [lastDeclineCode, setLastDeclineCode] = useState("");
  const [debitOrderReturns, setDebitOrderReturns] = useState("");
  const [knownSalaryDay, setKnownSalaryDay] = useState("");

  // Mobile money optional
  const [walletBalance7dAvg, setWalletBalance7dAvg] = useState("");
  const [walletBalanceCurrent, setWalletBalanceCurrent] = useState("");
  const [hoursSinceLastInflow, setHoursSinceLastInflow] = useState("");
  const [regularInflowDay, setRegularInflowDay] = useState("");
  const [activeLoanCount, setActiveLoanCount] = useState("");
  const [transactionsLast7d, setTransactionsLast7d] = useState("");
  const [transactionsAvg7d, setTransactionsAvg7d] = useState("");
  const [lastAirtimeDaysAgo, setLastAirtimeDaysAgo] = useState("");
  const [newLoanCycling, setNewLoanCycling] = useState<"" | "true" | "false">("");
  const [loansTakenLast90d, setLoansTakenLast90d] = useState("");

  const [submitting, setSubmitting] = useState(false);

  const buildCustomerData = (): CustomerData => {
    const cd: CustomerData = {};
    const setInt = (key: keyof CustomerData, raw: string) => {
      const v = parseInt(raw, 10);
      if (!Number.isNaN(v)) (cd as Record<string, unknown>)[key as string] = v;
    };
    const setNum = (key: keyof CustomerData, raw: string) => {
      const v = parseFloat(raw);
      if (!Number.isNaN(v)) (cd as Record<string, unknown>)[key as string] = v;
    };
    const setStr = (key: keyof CustomerData, raw: string) => {
      if (raw) (cd as Record<string, unknown>)[key as string] = raw;
    };
    const setBool = (key: keyof CustomerData, raw: string) => {
      if (raw === "true") (cd as Record<string, unknown>)[key as string] = true;
      else if (raw === "false") (cd as Record<string, unknown>)[key as string] = false;
    };
    const setList = (key: keyof CustomerData, raw: string) => {
      const list = raw.split("|").map((s) => s.trim()).filter(Boolean);
      if (list.length > 0) (cd as Record<string, unknown>)[key as string] = list;
    };

    setInt("total_payments", totalPayments);
    setInt("successful_payments", successfulPayments);
    setStr("last_successful_payment_date", lastSuccessfulPaymentDate);
    setNum("average_collection_amount", averageCollectionAmount);
    setInt("instalment_number", instalmentNumber);
    setInt("total_instalments", totalInstalments);

    if (method === "CARD" || method === "DEBIT_ORDER") {
      setStr("card_type", cardType);
      setStr("card_expiry_date", cardExpiryDate);
      setStr("last_decline_code", lastDeclineCode);
      setList("debit_order_returns", debitOrderReturns);
      setInt("known_salary_day", knownSalaryDay);
    }
    if (method === "MOBILE_MONEY") {
      setNum("wallet_balance_7d_avg", walletBalance7dAvg);
      setNum("wallet_balance_current", walletBalanceCurrent);
      setInt("hours_since_last_inflow", hoursSinceLastInflow);
      setStr("regular_inflow_day", regularInflowDay);
      setInt("active_loan_count", activeLoanCount);
      setInt("transactions_last_7d", transactionsLast7d);
      setInt("transactions_avg_7d", transactionsAvg7d);
      setInt("last_airtime_purchase_days_ago", lastAirtimeDaysAgo);
      setBool("new_loan_within_repayment_period", newLoanCycling);
      setInt("loans_taken_last_90d", loansTakenLast90d);
    }
    return cd;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload: ScoreRequestPayload = {
        customer_id: customerId,
        collection_id: collectionId,
        collection_amount: parseFloat(amount),
        collection_currency: currency,
        collection_due_date: dueDate,
        collection_method: method,
        customer_data: buildCustomerData(),
      };
      const result = await scoresApi.create(payload);
      onScored(result);
      toast.success("Scored");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Scoring failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardContent className="p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Required */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field name="customer_id" required>
              <Input
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                placeholder="cust_001"
                required
              />
            </Field>
            <Field name="collection_id" required>
              <Input
                value={collectionId}
                onChange={(e) => setCollectionId(e.target.value)}
                placeholder="inst_001"
                required
              />
            </Field>
            <Field name="collection_amount" required>
              <div className="flex gap-2">
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="833.33"
                  required
                  className="flex-1"
                />
                <Select
                  value={currency}
                  onValueChange={(v) => setCurrency(v as "ZAR" | "ZMW")}
                >
                  <SelectTrigger className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ZAR">ZAR</SelectItem>
                    <SelectItem value="ZMW">ZMW</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </Field>
            <Field name="collection_due_date" required>
              <Input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                required
              />
            </Field>
            <Field name="collection_method" required className="md:col-span-2">
              <Select value={method} onValueChange={(v) => setMethod(v as Method)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CARD">Card on file</SelectItem>
                  <SelectItem value="DEBIT_ORDER">Debit order</SelectItem>
                  <SelectItem value="MOBILE_MONEY">Mobile money</SelectItem>
                </SelectContent>
              </Select>
            </Field>
          </div>

          {/* Optional */}
          <div>
            <button
              type="button"
              onClick={() => setOptionalOpen((v) => !v)}
              className="flex w-full items-center justify-between rounded-md border border-border bg-muted/30 px-4 py-3 text-sm font-medium text-foreground transition-colors hover:bg-muted/50"
            >
              <span>
                Optional data — sharpens the score
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  (leave any cell blank if you don&apos;t have it)
                </span>
              </span>
              {optionalOpen ? (
                <ChevronDownIcon className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRightIcon className="h-4 w-4 text-muted-foreground" />
              )}
            </button>

            {optionalOpen && (
              <div className="mt-4 space-y-6">
                {/* Common */}
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field name="total_payments">
                    <Input
                      type="number"
                      min="0"
                      value={totalPayments}
                      onChange={(e) => setTotalPayments(e.target.value)}
                    />
                  </Field>
                  <Field name="successful_payments">
                    <Input
                      type="number"
                      min="0"
                      value={successfulPayments}
                      onChange={(e) => setSuccessfulPayments(e.target.value)}
                    />
                  </Field>
                  <Field name="last_successful_payment_date">
                    <Input
                      type="date"
                      value={lastSuccessfulPaymentDate}
                      onChange={(e) => setLastSuccessfulPaymentDate(e.target.value)}
                    />
                  </Field>
                  <Field name="average_collection_amount">
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={averageCollectionAmount}
                      onChange={(e) => setAverageCollectionAmount(e.target.value)}
                    />
                  </Field>
                  <Field name="instalment_number">
                    <Input
                      type="number"
                      min="1"
                      value={instalmentNumber}
                      onChange={(e) => setInstalmentNumber(e.target.value)}
                    />
                  </Field>
                  <Field name="total_instalments">
                    <Input
                      type="number"
                      min="1"
                      value={totalInstalments}
                      onChange={(e) => setTotalInstalments(e.target.value)}
                    />
                  </Field>
                </div>

                {/* Card / debit-order */}
                {(method === "CARD" || method === "DEBIT_ORDER") && (
                  <div className="space-y-3 border-t border-border pt-4">
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      {method === "CARD" ? "Card-specific" : "Debit-order-specific"}
                    </p>
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      {method === "CARD" && (
                        <>
                          <Field name="card_type">
                            <Select
                              value={cardType}
                              onValueChange={(v) => setCardType(v as "debit" | "credit")}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="—" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="debit">Debit</SelectItem>
                                <SelectItem value="credit">Credit</SelectItem>
                              </SelectContent>
                            </Select>
                          </Field>
                          <Field name="card_expiry">
                            <Input
                              type="date"
                              value={cardExpiryDate}
                              onChange={(e) => setCardExpiryDate(e.target.value)}
                            />
                          </Field>
                          <Field name="last_decline_code">
                            <Input
                              value={lastDeclineCode}
                              onChange={(e) => setLastDeclineCode(e.target.value)}
                              placeholder="insufficient_funds"
                            />
                          </Field>
                        </>
                      )}
                      {method === "DEBIT_ORDER" && (
                        <Field name="debit_order_returns" className="md:col-span-2">
                          <Input
                            value={debitOrderReturns}
                            onChange={(e) => setDebitOrderReturns(e.target.value)}
                            placeholder="RD|account_closed"
                          />
                        </Field>
                      )}
                      <Field name="known_salary_day">
                        <Input
                          type="number"
                          min="1"
                          max="31"
                          value={knownSalaryDay}
                          onChange={(e) => setKnownSalaryDay(e.target.value)}
                        />
                      </Field>
                    </div>
                  </div>
                )}

                {/* Mobile money */}
                {method === "MOBILE_MONEY" && (
                  <div className="space-y-3 border-t border-border pt-4">
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Mobile-money-specific
                    </p>
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      <Field name="wallet_balance_7d_avg">
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={walletBalance7dAvg}
                          onChange={(e) => setWalletBalance7dAvg(e.target.value)}
                        />
                      </Field>
                      <Field name="wallet_balance_current">
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={walletBalanceCurrent}
                          onChange={(e) => setWalletBalanceCurrent(e.target.value)}
                        />
                      </Field>
                      <Field name="hours_since_last_inflow">
                        <Input
                          type="number"
                          min="0"
                          value={hoursSinceLastInflow}
                          onChange={(e) => setHoursSinceLastInflow(e.target.value)}
                        />
                      </Field>
                      <Field name="regular_inflow_day">
                        <Select
                          value={regularInflowDay}
                          onValueChange={(v) => setRegularInflowDay(v ?? "")}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="—" />
                          </SelectTrigger>
                          <SelectContent>
                            {DAY_OF_WEEK_OPTIONS.map((day) => (
                              <SelectItem key={day} value={day}>
                                {day.charAt(0).toUpperCase() + day.slice(1)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </Field>
                      <Field name="active_loan_count">
                        <Input
                          type="number"
                          min="0"
                          value={activeLoanCount}
                          onChange={(e) => setActiveLoanCount(e.target.value)}
                        />
                      </Field>
                      <Field name="transactions_last_7d">
                        <Input
                          type="number"
                          min="0"
                          value={transactionsLast7d}
                          onChange={(e) => setTransactionsLast7d(e.target.value)}
                        />
                      </Field>
                      <Field name="transactions_avg_7d">
                        <Input
                          type="number"
                          min="0"
                          value={transactionsAvg7d}
                          onChange={(e) => setTransactionsAvg7d(e.target.value)}
                        />
                      </Field>
                      <Field name="last_airtime_purchase_days_ago">
                        <Input
                          type="number"
                          min="0"
                          value={lastAirtimeDaysAgo}
                          onChange={(e) => setLastAirtimeDaysAgo(e.target.value)}
                        />
                      </Field>
                      <Field name="loans_taken_last_90d">
                        <Input
                          type="number"
                          min="0"
                          value={loansTakenLast90d}
                          onChange={(e) => setLoansTakenLast90d(e.target.value)}
                        />
                      </Field>
                      <Field name="new_loan_within_repayment_period">
                        <Select
                          value={newLoanCycling}
                          onValueChange={(v) => setNewLoanCycling(v as "true" | "false")}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="—" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="false">No</SelectItem>
                            <SelectItem value="true">Yes</SelectItem>
                          </SelectContent>
                        </Select>
                      </Field>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Scoring…" : "Score this collection"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function Field({
  name,
  required,
  className,
  children,
}: {
  name: string;
  required?: boolean;
  className?: string;
  children: React.ReactNode;
}) {
  const help = getFieldHelp(name);
  return (
    <div className={className}>
      <Label className="text-sm">
        {getFieldLabel(name)}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {help && <p className="mt-0.5 text-xs text-muted-foreground">{help}</p>}
      <div className="mt-1.5">{children}</div>
    </div>
  );
}
