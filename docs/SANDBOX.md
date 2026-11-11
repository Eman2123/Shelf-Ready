# Running the full flow on the PayPal sandbox

No real money moves. Everything below uses sandbox accounts.

## 1. Get credentials (10 minutes)

1. Open <https://developer.paypal.com/dashboard/> and log in.
2. **Apps & Credentials**, switch to **Sandbox**, **Create App** (type Merchant). Copy **Client ID** and **Secret**.
3. **Testing Tools, Sandbox Accounts**: you get a Business (seller) and a Personal (buyer) account. Note the buyer email and password (View/Edit account shows the password).
4. Optional now, needed for the deployed flow: in the app, **Add Webhook** with the URL `https://<backend>/api/webhooks/paypal` and the events `CHECKOUT.ORDER.APPROVED`, `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.AUTHORIZATION.VOIDED`, `PAYMENT.CAPTURE.REFUNDED`. Copy the **Webhook ID**.

## 2. Run it locally with the script (no public URL needed)

```bash
cd backend
export PAYPAL_CLIENT_ID=...  PAYPAL_CLIENT_SECRET=...
python -m app.scripts.sandbox_e2e allow          # or: make sandbox SCENARIO=allow
```

The script prints a PayPal URL. Open it, log in with the **sandbox buyer**, approve. The script sees the approval, runs the same handler a webhook would, and prints the final status and the order log.

| Scenario | Expect | What it proves |
| --- | --- | --- |
| `allow` | CAPTURED | $36.00 inside the auto-approve limit: authorize, witness check, capture |
| `approval` | CAPTURED | $72.00 waits as AUTHORIZED until the seller approves, then captures |
| `reject` | VOIDED | seller rejects: the authorization is voided, nothing captured |
| `deny` | DENIED | $216.00 over the hard limit: code stops it, PayPal is never called |

Add `--refund` to `allow` to also test the refund. Check each result in the sandbox dashboard (**Testing Tools, Sandbox accounts, seller, Transactions**) and keep screenshots for the demo.

## 3. Run it through the real webhook (deployed backend)

1. Deploy the backend (README, Deploy) with `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `ADMIN_TOKEN`, `DATABASE_URL`.
2. Open `/app/keys` on the frontend, enter the admin token, create a key. Copy the raw key.
3. As an MCP client (or `curl` to `/mcp`) call `get_product`, then `create_order` with that key and the `quote_id`. The result has an `approval_url`.
4. Open it as the sandbox buyer and approve. PayPal calls the webhook; `/app/orders` shows the order move to CAPTURED (or to the approval queue if over $50).
5. `/app/orders`, "Load events" shows each webhook and its outcome.

## 4. If something fails

| Symptom | Cause |
| --- | --- |
| `PayPal 401 invalid_client` | wrong Client ID or Secret, or live keys used with the sandbox URL |
| `WEBHOOK_REJECTED` | `PAYPAL_WEBHOOK_ID` is not the id of the webhook that sent the event |
| order stays `CREATED` | the buyer has not approved, or the webhook is not reaching the backend (check "Recent deliveries" in the PayPal dashboard) |
| `WITNESS_MISMATCH` | PayPal's copy of the order differs from ours; the log shows which field, and the authorization is voided |
| `PayPal 422` on create | read `debug_id` in the log and search it in the PayPal dashboard API calls |

Paste any error here and it can be fixed.
