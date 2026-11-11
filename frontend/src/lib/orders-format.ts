import type { StatusKind } from "@/components/ui";
import type { ApiOrder, OrderStatus } from "@/lib/api/types";

export const money = (cents: number, currency = "USD"): string =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(cents / 100);

export const ORDER_KIND: Record<OrderStatus, StatusKind> = {
  CAPTURED: "ok",
  REFUNDED: "ok",
  AUTHORIZED: "wait",
  CREATED: "wait",
  NEEDS_APPROVAL: "wait",
  DENIED: "blocked",
  VOIDED: "blocked",
  FAILED: "blocked",
};

export type Stage = {
  name: "Identity" | "Data" | "Limits" | "Decision" | "PayPal";
  state: "pass" | "fail" | "skipped";
  note: string;
};

const IDENTITY = new Set(["KEY_UNKNOWN", "KEY_REVOKED", "KEY_EXPIRED", "KEY_SCOPE_MISSING"]);
const DATA = new Set(["PRICE_CHANGED", "STOCK_CHANGED", "QUOTE_EXPIRED", "OUT_OF_STOCK"]);

/**
 * The pipeline from PRD 4.7, derived from what the backend stored: the policy reason says which
 * stage stopped the order. Stages after the stopping one are "skipped".
 */
export function pipelineStages(order: Pick<ApiOrder, "decision" | "status" | "paypal_order_id">) {
  const { decision, reason, detail } = order.decision;
  const stoppedAt: Stage["name"] | null =
    decision !== "DENY"
      ? null
      : IDENTITY.has(reason)
        ? "Identity"
        : DATA.has(reason)
          ? "Data"
          : "Limits";
  const order_ = ["Identity", "Data", "Limits"] as const;
  const stages: Stage[] = order_.map((name) => {
    const stopIndex = stoppedAt ? order_.indexOf(stoppedAt as (typeof order_)[number]) : 99;
    const i = order_.indexOf(name);
    if (i < stopIndex) return { name, state: "pass", note: "ok" };
    if (i === stopIndex) return { name, state: "fail", note: detail ?? reason };
    return { name, state: "skipped", note: "not reached" };
  });
  stages.push({
    name: "Decision",
    state: decision === "DENY" ? "fail" : "pass",
    note: decision === "ALLOW" ? "ALLOW" : (detail ?? `${decision} (${reason})`),
  });
  const moved = order.paypal_order_id !== null;
  stages.push({
    name: "PayPal",
    state: decision === "DENY" ? "skipped" : moved ? "pass" : "fail",
    note: decision === "DENY" ? "no PayPal call" : moved ? `order ${order.status}` : "not created",
  });
  return stages;
}

export const canRefund = (o: Pick<ApiOrder, "status" | "capture_id">) =>
  o.status === "CAPTURED" && o.capture_id !== null;
