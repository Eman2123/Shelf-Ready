import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

/** Lazy connection: importing this file never connects, so demo mode and builds need no database. */
let cached: ReturnType<typeof drizzle<typeof schema>> | null = null;

export function getDb() {
  if (cached) return cached;
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set");
  // prepare: false keeps pooled connections (Neon/Supabase poolers) working
  const client = postgres(url, { prepare: false, max: 5 });
  cached = drizzle(client, { schema });
  return cached;
}

export { schema };
