import { z } from "zod";
import { Cents, CountryCode, Id } from "./common";
import { GuardedOrderItemSchema } from "./order";

/** Store MCP tools (PRD M5). Names and inputs are a contract; change only with a heads-up. */
export const SearchProductsInput = z.object({
  query: z.string().default(""),
  maxPriceCents: Cents.optional(),
  category: z.string().optional(),
  limit: z.number().int().positive().max(50).default(10),
});

export const GetProductInput = z.object({ productId: Id });

export const GetPolicyInput = z.object({});

export const CreateOrderInput = z.object({
  items: z.array(GuardedOrderItemSchema).min(1),
  shipToCountry: CountryCode,
  idempotencyKey: z.string().min(8),
});

export const STORE_TOOL_NAMES = [
  "search_products",
  "get_product",
  "get_policy",
  "create_order",
] as const;

export type StoreToolName = (typeof STORE_TOOL_NAMES)[number];
export type SearchProductsInput = z.infer<typeof SearchProductsInput>;
export type GetProductInput = z.infer<typeof GetProductInput>;
export type CreateOrderInput = z.infer<typeof CreateOrderInput>;
