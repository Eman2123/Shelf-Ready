/** Browser-side client for the FastAPI backend. Admin routes need the X-Admin-Token header. */

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

const TOKEN_KEY = "shelf-ready-admin-token";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
  ) {
    super(`${status} ${code}`);
  }
}

/** The token lives in sessionStorage only: it is gone when the tab closes. */
export function getAdminToken(): string {
  try {
    return window.sessionStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setAdminToken(token: string): void {
  try {
    if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
    else window.sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage blocked: the token stays in memory of the form only */
  }
}

/** FastAPI errors are `{"detail": "CODE"}` or `{"detail": {"error": "CODE"}}`. */
export function errorCode(body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "error" in detail) {
    return String((detail as { error: unknown }).error);
  }
  return "REQUEST_FAILED";
}

export async function api<T>(
  path: string,
  init: { method?: "GET" | "POST"; body?: unknown; admin?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (init.admin) headers["X-Admin-Token"] = getAdminToken();
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: init.method ?? "GET",
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    });
  } catch {
    throw new ApiError(0, "BACKEND_UNREACHABLE");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, errorCode(body));
  return body as T;
}

const MESSAGES: Record<string, string> = {
  BACKEND_UNREACHABLE: "The backend is not reachable. Is it running and is the API URL right?",
  ADMIN_TOKEN_INVALID: "The admin token was rejected. Enter it again.",
  ADMIN_DISABLED: "Admin routes are switched off: set ADMIN_TOKEN on the backend.",
  PAYPAL_NOT_CONNECTED: "PayPal is not connected: set the sandbox credentials on the backend.",
  PAYPAL_ERROR: "PayPal returned an error. Check the sandbox dashboard for the debug id.",
};

export const explain = (error: unknown): string =>
  error instanceof ApiError
    ? (MESSAGES[error.code] ?? `The backend answered ${error.code}.`)
    : "Something went wrong.";
