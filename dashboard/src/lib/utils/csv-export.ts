/**
 * Fetch all pages of a paginated list endpoint and return the flat list.
 * Stops at maxRows to avoid runaway memory use.
 *
 * The fetcher must accept (page, pageSize) and return a list response with
 * `items` and `pagination.total_pages`.
 */
export async function fetchAllPages<T>(
  fetcher: (page: number, pageSize: number) => Promise<{
    items: T[];
    pagination: { total_pages: number };
  }>,
  options: { pageSize?: number; maxRows?: number } = {},
): Promise<T[]> {
  const pageSize = options.pageSize ?? 100;
  const maxRows = options.maxRows ?? 5000;

  const all: T[] = [];
  let page = 1;
  let totalPages = 1;

  while (page <= totalPages && all.length < maxRows) {
    const res = await fetcher(page, pageSize);
    all.push(...res.items);
    totalPages = res.pagination.total_pages;
    page += 1;
  }

  return all.slice(0, maxRows);
}


/**
 * Convert an array of objects to CSV and trigger a browser download.
 * Quotes fields containing commas, quotes, or newlines.
 */
export function downloadCsv(filename: string, rows: Record<string, unknown>[]): void {
  if (rows.length === 0) return;

  const headers = Object.keys(rows[0]);
  const escape = (value: unknown): string => {
    if (value == null) return "";
    const str = String(value);
    if (str.includes(",") || str.includes('"') || str.includes("\n")) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const lines = [
    headers.join(","),
    ...rows.map((row) => headers.map((h) => escape(row[h])).join(",")),
  ];
  const csv = lines.join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
