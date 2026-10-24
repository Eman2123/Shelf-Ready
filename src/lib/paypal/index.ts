/**
 * Owner: P1. PayPal sandbox client: token manager (OAuth client credentials, auto refresh),
 * Catalog Products, Orders v2, webhook signature verification, PayPal-Request-Id on every write.
 */
const SANDBOX_BASE = "https://api-m.sandbox.paypal.com";

/** ShelfReady is sandbox-only. This guard refuses any non-sandbox base URL. */
export function paypalBase(): string {
  const base = process.env.PAYPAL_API_BASE || SANDBOX_BASE;
  if (!base.includes("sandbox")) {
    throw new Error("ShelfReady is sandbox-only. Refusing to use a non-sandbox PayPal base URL.");
  }
  return base;
}
