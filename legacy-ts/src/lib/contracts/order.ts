import { z } from "zod";
import { CountryCode, Id } from "./common";
import { PolicyResultSchema } from "./policy";

export const OrderStatus = z.enum([
  "DENIED",
  "NEEDS_APPROVAL",
  "CREATED",
  "AUTHORIZED",
  "CAPTURED",
  "VOIDED",
  "REFUNDED",
  "FAILED",
]);

export const GuardedOrderItemSchema = z.object({
  productId: Id,
  variantSku: z.string().nullable().optional(),
  quantity: z.number().int().positive(),
});

/** Input of createGuardedOrder, also the body of the store MCP create_order tool. */
export const GuardedOrderRequestSchema = z.object({
  /** raw agent key; only its hash is ever stored */
  agentKey: z.string().min(1),
  items: z.array(GuardedOrderItemSchema).min(1),
  shipToCountry: CountryCode,
  /** retry-safe: the same key never creates two PayPal orders */
  idempotencyKey: z.string().min(8),
});

export const GuardedOrderResultSchema = z.object({
  orderId: Id,
  status: OrderStatus,
  paypalOrderId: z.string().nullable(),
  decision: PolicyResultSchema,
  /** set when the order needs the seller or buyer to approve */
  approvalUrl: z.string().url().nullable(),
});

export type OrderStatus = z.infer<typeof OrderStatus>;
export type GuardedOrderRequest = z.infer<typeof GuardedOrderRequestSchema>;
export type GuardedOrderResult = z.infer<typeof GuardedOrderResultSchema>;
