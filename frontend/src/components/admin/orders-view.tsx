"use client";

import { useState } from "react";
import { Button, StatusTag } from "@/components/ui";
import { api } from "@/lib/api/client";
import type { ApiApproval, ApiOrder, ApiWebhookEvent } from "@/lib/api/types";
import { ORDER_KIND, canRefund, money, pipelineStages } from "@/lib/orders-format";
import { ErrorLine, useAction, useAdminResource } from "./use-admin";

const STATE_WORD = { pass: "PASS", fail: "STOP", skipped: "—" } as const;

function Pipeline({ order }: { order: ApiOrder }) {
  return (
    <ol className="mt-3 grid gap-px border border-ink bg-ink sm:grid-cols-5" aria-label="Pipeline">
      {pipelineStages(order).map((s) => (
        <li key={s.name} className="bg-paper p-2">
          <p className="text-xs font-semibold uppercase text-mute">{s.name}</p>
          <p
            className={`font-mono text-sm font-bold ${
              s.state === "fail" ? "text-signal" : s.state === "pass" ? "text-ok" : "text-mute"
            }`}
          >
            {STATE_WORD[s.state]}
          </p>
          <p className="text-xs">{s.note}</p>
        </li>
      ))}
    </ol>
  );
}

function OrderCard({ order, onChanged }: { order: ApiOrder; onChanged: () => void }) {
  const act = useAction(onChanged);
  return (
    <li className="border-b border-ink py-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-mono text-sm font-bold">{order.order_id}</p>
        <StatusTag kind={ORDER_KIND[order.status]}>{order.status}</StatusTag>
      </div>
      <p className="mt-1 text-sm">
        <span className="font-mono text-xl font-bold">
          {money(order.total_cents, order.currency)}
        </span>{" "}
        · agent {order.agent_id} · {order.items.length} item(s)
      </p>
      <Pipeline order={order} />
      {order.failure && <p className="mt-2 text-sm text-signal">{order.failure}</p>}
      <p className="mt-2 font-mono text-xs text-mute">
        PayPal order {order.paypal_order_id ?? "none"}
        {order.capture_id ? ` · capture ${order.capture_id}` : ""}
      </p>
      {canRefund(order) && (
        <div className="mt-3">
          <Button
            variant="secondary"
            disabled={act.busy !== null}
            onClick={() =>
              act.run("refund", () =>
                api(`/api/orders/${order.order_id}/refund`, {
                  method: "POST",
                  body: {},
                  admin: true,
                }),
              )
            }
          >
            Refund in full
          </Button>
        </div>
      )}
      <ErrorLine message={act.error} />
    </li>
  );
}

function Approvals({ items, onChanged }: { items: ApiApproval[]; onChanged: () => void }) {
  const act = useAction(onChanged);
  const pending = items.filter((a) => a.status === "PENDING");
  return (
    <section aria-label="Approval queue" className="mb-10">
      <h2 className="font-display text-3xl font-bold">Approval queue</h2>
      <ErrorLine message={act.error} />
      {pending.length === 0 ? (
        <p className="mt-2 text-mute">Nothing is waiting for you.</p>
      ) : (
        <ul className="mt-3 border-t-4 border-ink">
          {pending.map((a) => (
            <li
              key={a.approval_id}
              className="flex flex-wrap items-center gap-4 border-b border-ink py-3"
            >
              <div className="min-w-0 flex-1">
                <p className="font-mono text-sm font-bold">{a.order_id}</p>
                <p className="text-sm">
                  {a.detail ?? a.reason} · expires {new Date(a.expires_at).toLocaleString()}
                </p>
              </div>
              <Button
                disabled={act.busy !== null}
                onClick={() =>
                  act.run(a.approval_id, () =>
                    api(`/api/approvals/${a.approval_id}/approve`, { method: "POST", admin: true }),
                  )
                }
              >
                Approve
              </Button>
              <Button
                variant="secondary"
                disabled={act.busy !== null}
                onClick={() =>
                  act.run(a.approval_id, () =>
                    api(`/api/approvals/${a.approval_id}/reject`, { method: "POST", admin: true }),
                  )
                }
              >
                Reject
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function WebhookLog() {
  const [open, setOpen] = useState(false);
  const events = useAdminResource<{ events: ApiWebhookEvent[] }>("/api/webhooks/events", open);
  return (
    <section aria-label="Webhook log" className="mt-10">
      <h2 className="font-display text-3xl font-bold">Webhook log</h2>
      {!open ? (
        <Button variant="secondary" className="mt-3" onClick={() => setOpen(true)}>
          Load events
        </Button>
      ) : (
        <>
          <ErrorLine message={events.error} />
          <table className="mt-3 w-full text-left text-sm">
            <thead className="border-b-2 border-ink text-xs uppercase text-mute">
              <tr>
                <th className="py-1">Event</th>
                <th>Resource</th>
                <th>Outcome</th>
                <th>Received</th>
              </tr>
            </thead>
            <tbody>
              {(events.data?.events ?? []).map((e) => (
                <tr key={e.event_id} className="border-b border-ink/30">
                  <td className="py-1 font-mono text-xs">{e.event_type}</td>
                  <td className="font-mono text-xs">{e.resource_id ?? "—"}</td>
                  <td className="font-bold">{e.outcome}</td>
                  <td className="text-xs">{new Date(e.received_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {events.data?.events.length === 0 && <p className="mt-2 text-mute">No events yet.</p>}
        </>
      )}
    </section>
  );
}

export function OrdersView() {
  const orders = useAdminResource<{ orders: ApiOrder[] }>("/api/orders", true);
  const approvals = useAdminResource<{ approvals: ApiApproval[] }>("/api/approvals", true);
  const reload = () => {
    void orders.reload();
    void approvals.reload();
  };
  const list = orders.data?.orders ?? [];
  return (
    <div>
      <ErrorLine message={orders.error ?? approvals.error} />
      <div className="mb-6">
        <Button variant="secondary" onClick={reload} disabled={orders.loading}>
          {orders.loading ? "Loading…" : "Refresh"}
        </Button>
      </div>
      <Approvals items={approvals.data?.approvals ?? []} onChanged={reload} />
      <h2 className="font-display text-3xl font-bold">Orders</h2>
      {orders.data && list.length === 0 && (
        <p className="mt-2 text-mute">No orders yet. An agent order will appear here.</p>
      )}
      <ul className="mt-3 border-t-4 border-ink">
        {list.map((o) => (
          <OrderCard key={o.order_id} order={o} onChanged={reload} />
        ))}
      </ul>
      <WebhookLog />
    </div>
  );
}
