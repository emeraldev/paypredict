export type Currency = "ZAR" | "ZMW";

export function formatCurrency(amount: number, currency: Currency): string {
  const symbol = currency === "ZAR" ? "R" : "ZMW";
  return `${symbol}${amount.toLocaleString("en-ZA", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatCompactCurrency(amount: number, currency: Currency): string {
  const symbol = currency === "ZAR" ? "R" : "ZMW";
  if (amount >= 1_000_000) {
    return `${symbol}${(amount / 1_000_000).toFixed(1)}M`;
  }
  if (amount >= 1_000) {
    return `${symbol}${(amount / 1_000).toFixed(1)}k`;
  }
  return `${symbol}${amount.toFixed(0)}`;
}
