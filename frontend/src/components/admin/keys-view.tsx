"use client";

import { useState } from "react";
import { Button, StatusTag } from "@/components/ui";
import { api } from "@/lib/api/client";
import type { ApiKey } from "@/lib/api/types";
import { money } from "@/lib/orders-format";
import { ErrorLine, useAction, useAdminResource } from "./use-admin";

const SCOPES = ["read", "quote", "order"] as const;

function CreateKey({ onCreated }: { onCreated: () => void }) {
  const [agent, setAgent] = useState("agent-1");
  const [scopes, setScopes] = useState<string[]>(["read", "quote", "order"]);
  const [perOrder, setPerOrder] = useState("100");
  const [perDay, setPerDay] = useState("300");
  const [rawKey, setRawKey] = useState<string | null>(null);
  const act = useAction(onCreated);

  const submit = () =>
    act.run("create", async () => {
      const res = await api<{ raw_key: string }>("/api/keys", {
        method: "POST",
        admin: true,
        body: {
          agent_id: agent,
          scopes,
          per_order_max_cents: Math.round(Number(perOrder) * 100),
          per_day_budget_cents: Math.round(Number(perDay) * 100),
          allowed_categories: ["apparel", "bags", "home"],
        },
      });
      setRawKey(res.raw_key);
    });

  const field = "mt-1 min-h-11 border-2 border-ink bg-paper px-3 text-sm text-ink";
  return (
    <section aria-label="Create key" className="mb-10">
      <h2 className="font-display text-3xl font-bold">New agent key</h2>
      <form
        className="mt-3 flex flex-wrap items-end gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <label className="flex flex-col text-xs font-semibold uppercase text-mute">
          Agent name
          <input
            className={field}
            value={agent}
            onChange={(e) => setAgent(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col text-xs font-semibold uppercase text-mute">
          Max per order ($)
          <input
            className={`${field} w-32`}
            type="number"
            min="0"
            value={perOrder}
            onChange={(e) => setPerOrder(e.target.value)}
          />
        </label>
        <label className="flex flex-col text-xs font-semibold uppercase text-mute">
          Daily budget ($)
          <input
            className={`${field} w-32`}
            type="number"
            min="0"
            value={perDay}
            onChange={(e) => setPerDay(e.target.value)}
          />
        </label>
        <fieldset className="flex gap-3 text-sm">
          <legend className="text-xs font-semibold uppercase text-mute">Scopes</legend>
          {SCOPES.map((s) => (
            <label key={s} className="flex min-h-11 items-center gap-1">
              <input
                type="checkbox"
                checked={scopes.includes(s)}
                onChange={(e) =>
                  setScopes(e.target.checked ? [...scopes, s] : scopes.filter((x) => x !== s))
                }
              />
              {s}
            </label>
          ))}
        </fieldset>
        <Button type="submit" disabled={act.busy !== null || scopes.length === 0}>
          Create key
        </Button>
      </form>
      <ErrorLine message={act.error} />
      {rawKey && (
        <div role="status" className="mt-4 border-2 border-ink bg-hilite p-3">
          <p className="text-xs font-extrabold uppercase">Shown once. Copy it now.</p>
          <code className="break-all font-mono text-sm">{rawKey}</code>
        </div>
      )}
    </section>
  );
}

export function KeysView() {
  const keys = useAdminResource<{ keys: ApiKey[] }>("/api/keys", true);
  const act = useAction(keys.reload);
  return (
    <div>
      <ErrorLine message={keys.error} />
      <CreateKey onCreated={keys.reload} />
      <h2 className="font-display text-3xl font-bold">Keys</h2>
      <ErrorLine message={act.error} />
      {keys.data && keys.data.keys.length === 0 && <p className="mt-2 text-mute">No keys yet.</p>}
      <ul className="mt-3 border-t-4 border-ink">
        {(keys.data?.keys ?? []).map((k) => (
          <li key={k.key_id} className="flex flex-wrap items-center gap-4 border-b border-ink py-3">
            <div className="min-w-0 flex-1">
              <p className="font-mono text-sm font-bold">
                {k.key_id} · {k.agent_id}
              </p>
              <p className="text-sm">
                scopes {k.scopes.join(", ")} · {money(k.limits.per_order_max_cents)} per order ·{" "}
                {money(k.limits.per_day_budget_cents)} per day
              </p>
            </div>
            {k.revoked_at ? (
              <StatusTag kind="blocked">Revoked</StatusTag>
            ) : (
              <>
                <StatusTag kind="ok">Active</StatusTag>
                <Button
                  variant="secondary"
                  disabled={act.busy !== null}
                  onClick={() =>
                    act.run(k.key_id, () =>
                      api(`/api/keys/${k.key_id}/revoke`, { method: "POST", admin: true }),
                    )
                  }
                >
                  Revoke
                </Button>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
