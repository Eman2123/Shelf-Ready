import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * PayPal webhook receiver (owner: P1). TODO:
 * 1. read the raw body, 2. verify the signature through PayPal's verification API,
 * 3. insert into webhook_events (unique paypal_event_id) and skip duplicates,
 * 4. handle delayed and out-of-order events without ever capturing twice.
 * Returns 501 until implemented so events are not silently dropped.
 */
export function POST() {
  return NextResponse.json({ error: "not_implemented" }, { status: 501 });
}
