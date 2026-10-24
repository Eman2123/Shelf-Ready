import { z } from "zod";
import { Cents, CountryCode, CurrencyCode, Id } from "./common";

/** One normalized product record. Every importer and the PayPal connector must produce this. */
export const VariantSchema = z.object({
  sku: z.string().nullable(),
  /** e.g. { size: "M", color: "blue", material: "cotton" } */
  attributes: z.record(z.string(), z.string()),
  priceCents: Cents.nullable(),
  /** null = stock not stated by the seller (an audit issue), 0 = out of stock */
  stock: z.number().int().nonnegative().nullable(),
});

export const ShippingSchema = z.object({
  regions: z.array(CountryCode),
  costCents: Cents.nullable(),
  minDays: z.number().int().nonnegative().nullable(),
  maxDays: z.number().int().nonnegative().nullable(),
});

export const ReturnsSchema = z.object({
  windowDays: z.number().int().nonnegative().nullable(),
  freeReturns: z.boolean().nullable(),
  policyText: z.string().nullable(),
});

export const ImageSchema = z.object({
  url: z.string().url(),
  alt: z.string().nullable(),
});

export const ProductSchema = z.object({
  id: Id,
  storeId: Id,
  paypalProductId: z.string().nullable(),
  name: z.string().min(1),
  description: z.string(),
  /** null when the source only says something vague such as "from $20" */
  priceCents: Cents.nullable(),
  /** the raw price text exactly as found in the source, kept for provenance */
  priceText: z.string().nullable(),
  currency: CurrencyCode,
  /** product-level stock; null = not stated */
  stock: z.number().int().nonnegative().nullable(),
  variants: z.array(VariantSchema),
  shipping: ShippingSchema.nullable(),
  returns: ReturnsSchema.nullable(),
  sku: z.string().nullable(),
  gtin: z.string().nullable(),
  images: z.array(ImageSchema),
  category: z.string().nullable(),
  homeUrl: z.string().url().nullable(),
  /** true when checkout needs a human step (for example "confirm size by phone") */
  checkoutRequiresHuman: z.boolean(),
  /** hash of the normalized source data, used for dedupe and drift detection */
  sourceHash: z.string().min(1),
});

export type Variant = z.infer<typeof VariantSchema>;
export type Shipping = z.infer<typeof ShippingSchema>;
export type Returns = z.infer<typeof ReturnsSchema>;
export type Product = z.infer<typeof ProductSchema>;
