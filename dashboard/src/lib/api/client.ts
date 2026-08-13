import type { ApiErrorBody, FastApiValidationError } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
const TOKEN_KEY = "paypredict_token";

// ---- Token management ----

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ---- API error ----

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Turn FastAPI's `detail` into a human-readable string.
 *
 * Plain `HTTPException` sends `detail: "some message"` — pass through.
 * Pydantic validation (422) sends `detail: [{loc, msg, ...}, ...]` —
 * flatten each item to `field.path: msg` and join. Without this the
 * default `String()` cast surfaces `[object Object]` in the toast.
 */
function formatDetail(
  detail: string | FastApiValidationError[] | undefined,
): string | undefined {
  if (!detail) return undefined;
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return undefined;
  return detail
    .map((err) => {
      // Drop the leading `body` / `query` / `path` segment; the rest is
      // the field path the caller actually cares about.
      const path = err.loc.slice(1).join(".") || err.loc.join(".");
      return path ? `${path}: ${err.msg}` : err.msg;
    })
    .join("; ");
}

// ---- Request ----

interface RequestOptions extends RequestInit {
  /** Skip auth header (for login endpoint) */
  skipAuth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuth, ...fetchOptions } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers as Record<string, string> | undefined),
  };

  if (!skipAuth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers,
  });

  // On 401, clear stale token
  if (res.status === 401 && !skipAuth) {
    clearToken();
  }

  if (!res.ok) {
    const body: ApiErrorBody = await res.json().catch(() => ({}));
    const code = body?.error?.code || "UNKNOWN";
    const message =
      body?.error?.message || formatDetail(body?.detail) || res.statusText;
    throw new ApiError(res.status, code, message);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),
};
