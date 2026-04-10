import { Card, CardContent } from "@/components/ui/card";
import type { CustomerData } from "@/lib/api/types";
import { formatDate } from "@/lib/utils/format-date";

interface CustomerContextCardsProps {
  customer: CustomerData;
}

interface ContextItem {
  label: string;
  value: string | number;
}

function buildContextItems(customer: CustomerData): ContextItem[] {
  const items: ContextItem[] = [];

  if (customer.total_payments !== undefined && customer.total_payments > 0) {
    const successRate = customer.successful_payments
      ? Math.round((customer.successful_payments / customer.total_payments) * 100)
      : 0;
    items.push({
      label: "Payment History",
      value: `${customer.successful_payments ?? 0}/${customer.total_payments} (${successRate}%)`,
    });
  }

  if (customer.last_successful_payment_date) {
    items.push({
      label: "Last Successful",
      value: formatDate(customer.last_successful_payment_date),
    });
  }

  if (customer.instalment_number && customer.total_instalments) {
    items.push({
      label: "Instalment",
      value: `${customer.instalment_number} of ${customer.total_instalments}`,
    });
  }

  if (customer.average_collection_amount) {
    items.push({
      label: "Avg Amount",
      value: customer.average_collection_amount.toFixed(2),
    });
  }

  // Card-specific
  if (customer.card_type) {
    items.push({ label: "Card Type", value: customer.card_type });
  }
  if (customer.card_expiry_date) {
    items.push({ label: "Card Expires", value: formatDate(customer.card_expiry_date) });
  }

  // Wallet-specific
  if (customer.wallet_balance_current !== undefined && customer.wallet_balance_current !== null) {
    items.push({
      label: "Wallet Balance",
      value: customer.wallet_balance_current.toFixed(2),
    });
  }
  if (
    customer.hours_since_last_inflow !== undefined &&
    customer.hours_since_last_inflow !== null
  ) {
    items.push({
      label: "Last Inflow",
      value: `${customer.hours_since_last_inflow}h ago`,
    });
  }

  return items;
}

export function CustomerContextCards({ customer }: CustomerContextCardsProps) {
  const items = buildContextItems(customer);

  if (items.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">No customer context data provided.</p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map((item) => (
        <Card key={item.label} className="border-border/60 bg-muted/40">
          <CardContent className="p-3">
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="mt-1 text-sm font-semibold text-foreground">{item.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
