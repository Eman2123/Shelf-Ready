"use client";

import { useEffect, useState } from "react";
import { Button, StatusTag } from "@/components/ui";
import { API_BASE, api, explain } from "@/lib/api/client";
import type { CatalogSync, Health } from "@/lib/api/types";
import { ErrorLine, useAction } from "./use-admin";

export function ConnectView() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sync, setSync] = useState<CatalogSync | null>(null);
  const act = useAction();

  useEffect(() => {
    api<Health>("/health")
      .then(setHealth)
      .catch((e) => setError(explain(e)));
  }, []);

  return (
    <div>
      <ErrorLine message={error} />
      <dl className="grid max-w-xl grid-cols-2 border-y border-ink text-sm">
        <dt className="py-2 text-xs font-semibold uppercase text-mute">Backend</dt>
        <dd className="py-2 font-mono">{API_BASE}</dd>
        <dt className="py-2 text-xs font-semibold uppercase text-mute">API</dt>
        <dd className="py-2">
          {health ? (
            <StatusTag kind="ok">Up</StatusTag>
          ) : (
            <StatusTag kind="wait">Checking</StatusTag>
          )}
        </dd>
        <dt className="py-2 text-xs font-semibold uppercase text-mute">PayPal sandbox</dt>
        <dd className="py-2">
          {health?.paypal === "connected" ? (
            <StatusTag kind="ok">Connected</StatusTag>
          ) : (
            <StatusTag kind="blocked">Not connected</StatusTag>
          )}
        </dd>
      </dl>

      <section aria-label="Catalog sync" className="mt-10">
        <h2 className="font-display text-3xl font-bold">PayPal catalog</h2>
        <p className="mt-2 max-w-xl text-sm">
          Reads the products in your PayPal sandbox catalog and shows what a sync would add or
          update. The published demo catalog is not changed.
        </p>
        <Button
          className="mt-3"
          disabled={act.busy !== null || health?.paypal !== "connected"}
          onClick={() =>
            act.run("sync", async () => {
              setSync(
                await api<CatalogSync>("/api/paypal/catalog/sync", { method: "POST", admin: true }),
              );
            })
          }
        >
          {act.busy ? "Reading…" : "Preview catalog sync"}
        </Button>
        <ErrorLine message={act.error} />
        {sync && (
          <p role="status" className="mt-3 font-mono text-sm">
            fetched {sync.fetched} · would add {sync.added.length} · update {sync.updated.length} ·
            unchanged {sync.skipped.length}
          </p>
        )}
      </section>
    </div>
  );
}
