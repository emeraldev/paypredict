"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Generic hook for fetching data from the API.
 * Re-fetches whenever `deps` change (like useEffect deps).
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Track the latest fetch to avoid stale updates
  const fetchId = useRef(0);

  const refetch = useCallback(async () => {
    const id = ++fetchId.current;
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      if (id === fetchId.current) {
        setData(result);
      }
    } catch (err) {
      if (id === fetchId.current) {
        setError(err instanceof Error ? err.message : "An error occurred");
      }
    } finally {
      if (id === fetchId.current) {
        setLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    refetch();
  }, [refetch]);

  return { data, loading, error, refetch };
}
