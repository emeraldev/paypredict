export type Currency = "ZAR" | "ZMW";

/**
 * Format money with accounting conventions:
 * - symbol prefix (R / ZMW) glued to the digits, never separated by the sign
 * - negatives wrapped in parens: `-1234.56` -> `(R1 234,56)`
 * - localised digit grouping via `en-ZA`
 *
 * Callers currently only pass non-negative amounts (collection amount,
 * amount_collected, etc.) but the paren treatment matters for future
 * refund / adjustment / delta surfaces.
 */
export function formatCurrency(amount: number, currency: Currency): string {
  const symbol = currency === "ZAR" ? "R" : "ZMW";
  const absolute = Math.abs(amount).toLocaleString("en-ZA", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const formatted = `${symbol}${absolute}`;
  return amount < 0 ? `(${formatted})` : formatted;
}

/**
 * Compact form for hero numbers and stat cards: `R1.2M`, `ZMW340k`.
 * Bucket selection uses the absolute value so the M/k suffix applies to
 * negatives too — a bug in the previous implementation dropped negatives
 * of any magnitude into the fully-expanded fallback branch.
 */
export function formatCompactCurrency(amount: number, currency: Currency): string {
  const symbol = currency === "ZAR" ? "R" : "ZMW";
  const abs = Math.abs(amount);
  let body: string;
  if (abs >= 1_000_000) {
    body = `${symbol}${(abs / 1_000_000).toFixed(1)}M`;
  } else if (abs >= 1_000) {
    body = `${symbol}${(abs / 1_000).toFixed(1)}k`;
  } else {
    body = `${symbol}${abs.toFixed(0)}`;
  }
  return amount < 0 ? `(${body})` : body;
}
