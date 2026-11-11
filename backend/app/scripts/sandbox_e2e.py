"""Run the real money path once against the PayPal SANDBOX (no mocks).

    PAYPAL_CLIENT_ID=... PAYPAL_CLIENT_SECRET=... python -m app.scripts.sandbox_e2e allow

Scenarios:
  allow     $36.00 order, inside the auto-approve limit: captured after you approve at PayPal
  approval  $72.00 order, needs the seller: stays AUTHORIZED until approved here, then captured
  reject    $72.00 order, seller rejects: the authorization is voided
  deny      $216.00 order, over the hard limit: stopped by code, PayPal is never called

Without a public webhook URL this script plays the webhook's part: it polls PayPal until you
have approved the payment, then runs the same handler a CHECKOUT.ORDER.APPROVED event would.
Add --refund to refund a captured order at the end.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from typing import Any, TextIO

from app.contracts import GuardedOrderItem, GuardedOrderRequest, KeyLimits, KeyScope
from app.db.repositories import OrderRepository
from app.services.keys import KeyStore
from app.services.mcp_store import StoreService
from app.services.orders import OrderService
from app.services.paypal import PayPalConfigError, PayPalOrders

SCENARIOS: dict[str, tuple[str, int]] = {
    "allow": ("prod_mug", 2),
    "approval": ("prod_tote", 3),
    "reject": ("prod_tote", 3),
    "deny": ("prod_tote", 9),
}
BUYER_DONE = {"APPROVED", "COMPLETED"}


async def run(
    scenario: str,
    *,
    store: StoreService,
    keys: KeyStore,
    orders: OrderService,
    repo: OrderRepository,
    paypal: PayPalOrders,
    poll_seconds: float = 3.0,
    timeout_seconds: float = 300.0,
    refund: bool = False,
    out: TextIO = sys.stdout,
) -> dict[str, Any]:
    def say(msg: str) -> None:
        print(msg, file=out, flush=True)

    product_id, qty = SCENARIOS[scenario]
    issued = keys.create_key(
        "sandbox-e2e",
        "store_demo",
        [KeyScope.READ, KeyScope.QUOTE, KeyScope.ORDER],
        KeyLimits(
            per_order_max_cents=100_000,
            per_day_budget_cents=100_000,
            requests_per_minute=100,
            allowed_categories=["apparel", "bags", "home"],
            expires_at=None,
        ),
    )
    product = store.products[product_id]
    quote = store.issue_quote(product, product.variants[0].sku if product.variants else None)
    assert quote is not None
    say(f"1. quote {quote.quote_id}: {product.name} x{qty} @ {quote.unit_price_cents} cents")

    result = await orders.create(
        GuardedOrderRequest(
            agent_key=issued.raw_key,
            items=[
                GuardedOrderItem(
                    product_id=product_id,
                    variant_sku=quote.variant_sku,
                    quantity=qty,
                    quote_id=quote.quote_id,
                )
            ],
            ship_to_country="US",
            idempotency_key=f"e2e-{scenario}-{int(time.time())}",
        )
    )
    say(
        f"2. policy: {result.decision.decision.value} ({result.decision.reason.value}) "
        f"-> order {result.order_id} is {result.status.value}"
    )
    if result.paypal_order_id is None:
        say("   PayPal was not called (stopped by code, or PayPal rejected the create).")
        return {"order": repo.get(result.order_id), "approval": None}

    say(f"3. PayPal order {result.paypal_order_id} created.")
    say(f"   OPEN THIS URL, log in as your SANDBOX BUYER and approve:\n   {result.approval_url}")
    deadline = time.monotonic() + timeout_seconds
    while True:
        status = (await paypal.get_order(result.paypal_order_id)).get("status")
        if status in BUYER_DONE:
            break
        if time.monotonic() > deadline:
            say("   Timed out waiting for the buyer approval.")
            return {"order": repo.get(result.order_id), "approval": None}
        await asyncio.sleep(poll_seconds)
    say(f"4. buyer approved (PayPal status {status}). Running the webhook handler.")
    say(f"   -> {await orders.on_buyer_approved(result.paypal_order_id)}")

    approval = repo.approval_for_order(result.order_id)
    if approval is not None and approval.status == "PENDING":
        if scenario == "reject":
            say(f"5. seller REJECTS -> {await orders.reject(approval.id)}")
        else:
            say(f"5. seller APPROVES -> {await orders.approve(approval.id)}")

    final = repo.get(result.order_id)
    say(
        f"6. final status: {final.status}  capture={final.capture_id}  auth={final.authorization_id}"
    )
    if refund and final.status == "CAPTURED":
        say(f"7. refund -> {await orders.refund(final.id)}")
        final = repo.get(result.order_id)
    for event in repo.events(result.order_id):
        say(f"   log: {event.type} {event.detail}")
    return {"order": final, "approval": approval}


async def main_async(args: argparse.Namespace) -> int:
    from app.core import runtime

    if runtime.paypal_client is None:
        raise PayPalConfigError("Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET first.")
    await runtime.paypal_client.get_access_token()  # fails fast on wrong credentials
    print("0. PayPal sandbox credentials accepted.")
    result = await run(
        args.scenario,
        store=runtime.store_service,
        keys=runtime.key_store,
        orders=runtime.order_service,
        repo=runtime.order_repo,
        paypal=PayPalOrders(runtime.paypal_client),
        refund=args.refund,
        timeout_seconds=args.timeout,
    )
    expected = {"allow": "CAPTURED", "approval": "CAPTURED", "reject": "VOIDED", "deny": "DENIED"}
    status = result["order"].status
    if args.refund and status == "REFUNDED":
        status = "CAPTURED"
    ok = status == expected[args.scenario]
    print(f"\n{'PASS' if ok else 'FAIL'}: expected {expected[args.scenario]}, got {status}")
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--refund", action="store_true")
    parser.add_argument("--timeout", type=float, default=300.0, help="seconds to wait for buyer")
    sys.exit(asyncio.run(main_async(parser.parse_args())))


if __name__ == "__main__":
    main()
