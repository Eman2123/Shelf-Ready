import {
  CreateOrderInput,
  GetPolicyInput,
  GetProductInput,
  SearchProductsInput,
} from "@/lib/contracts";
import { demoPolicyRules, fixtureProducts } from "@/lib/fixtures/products";

/**
 * Store MCP tools (owner: P2). Definitions are the contract; handlers below are fixture-backed
 * stubs so the buyer agent (P3) can start. Every real call must pass an agent key check (P1).
 */
export const STORE_TOOL_DEFS = [
  {
    name: "search_products",
    description: "Search products by text, max price and category. Returns structured data.",
    inputSchema: SearchProductsInput,
  },
  {
    name: "get_product",
    description: "Get one product with price, stock, variants, shipping and returns.",
    inputSchema: GetProductInput,
  },
  {
    name: "get_policy",
    description: "Get the store's purchase rules (limits, categories, shipping regions).",
    inputSchema: GetPolicyInput,
  },
  {
    name: "create_order",
    description: "Create a guarded order. May return NEEDS_APPROVAL or DENY with a reason code.",
    inputSchema: CreateOrderInput,
  },
] as const;

export async function searchProducts(input: SearchProductsInput) {
  const q = input.query.trim().toLowerCase();
  return fixtureProducts
    .filter((p) => (q ? `${p.name} ${p.description}`.toLowerCase().includes(q) : true))
    .filter((p) => (input.category ? p.category === input.category : true))
    .filter((p) =>
      input.maxPriceCents === undefined || p.priceCents === null
        ? true
        : p.priceCents <= input.maxPriceCents,
    )
    .slice(0, input.limit);
}

export async function getProduct(input: GetProductInput) {
  return fixtureProducts.find((p) => p.id === input.productId) ?? null;
}

export async function getPolicy() {
  return demoPolicyRules;
}
