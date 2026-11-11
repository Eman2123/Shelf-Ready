import { describe, expect, it } from "vitest";
import { canRefund, money, pipelineStages } from "@/lib/orders-format";
import { errorCode } from "@/lib/api/client";

const decision = (d: string, reason: string, detail: string | null = null) =>
  ({ decision: d, reason, detail }) as never;

describe("orders format", () => {
  it("formats integer cents without floats", () => {
    expect(money(18000)).toBe("$180.00");
    expect(money(5)).toBe("$0.05");
  });

  it("stops the pipeline at the limits stage for an over-limit order", () => {
    const stages = pipelineStages({
      decision: decision("DENY", "OVER_HARD_LIMIT", "$216.00 > hard limit $200.00"),
      status: "DENIED",
      paypal_order_id: null,
    });
    expect(stages.map((s) => s.state)).toEqual(["pass", "pass", "fail", "fail", "skipped"]);
    expect(stages[2].note).toContain("$216.00");
    expect(stages[4].note).toBe("no PayPal call");
  });

  it("stops at identity for a revoked key and skips the rest", () => {
    const stages = pipelineStages({
      decision: decision("DENY", "KEY_REVOKED"),
      status: "DENIED",
      paypal_order_id: null,
    });
    expect(stages.map((s) => s.state)).toEqual(["fail", "skipped", "skipped", "fail", "skipped"]);
  });

  it("passes every stage for an allowed order that reached PayPal", () => {
    const stages = pipelineStages({
      decision: decision("ALLOW", "AUTO_APPROVED"),
      status: "CAPTURED",
      paypal_order_id: "PP-1",
    });
    expect(stages.every((s) => s.state === "pass")).toBe(true);
  });

  it("only offers a refund for a captured order", () => {
    expect(canRefund({ status: "CAPTURED", capture_id: "C1" })).toBe(true);
    expect(canRefund({ status: "AUTHORIZED", capture_id: null })).toBe(false);
  });

  it("reads FastAPI error bodies", () => {
    expect(errorCode({ detail: "ORDER_NOT_FOUND" })).toBe("ORDER_NOT_FOUND");
    expect(errorCode({ detail: { error: "PAYPAL_ERROR" } })).toBe("PAYPAL_ERROR");
    expect(errorCode(null)).toBe("REQUEST_FAILED");
  });
});
