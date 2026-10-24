import { z } from "zod";

/**
 * Shared primitives for every contract.
 * Rule: money is always an integer in minor units (cents) plus a 3-letter currency code.
 */
export const Id = z.string().min(1);
export const CurrencyCode = z.string().regex(/^[A-Z]{3}$/, "ISO 4217 code, upper case");
export const Cents = z.number().int().nonnegative();
export const IsoDateTime = z.string().datetime();
export const CountryCode = z.string().regex(/^[A-Z]{2}$/, "ISO 3166-1 alpha-2, upper case");

export type CurrencyCodeT = z.infer<typeof CurrencyCode>;
