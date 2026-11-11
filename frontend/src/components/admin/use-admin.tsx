"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui";
import { api, explain, getAdminToken, setAdminToken } from "@/lib/api/client";

/** Loads an admin route and exposes reload. `enabled` waits until a token is entered. */
export function useAdminResource<T>(path: string, enabled: boolean) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    try {
      setData(await api<T>(path, { admin: true }));
      setError(null);
    } catch (e) {
      setError(explain(e));
    } finally {
      setLoading(false);
    }
  }, [path, enabled]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, error, loading, reload };
}

/** Runs one admin action, tracks busy and error. */
export function useAction(onDone?: () => void | Promise<void>) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const run = async (id: string, fn: () => Promise<unknown>) => {
    setBusy(id);
    setError(null);
    try {
      await fn();
      await onDone?.();
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(null);
    }
  };
  return { busy, error, run };
}

/**
 * Admin screens need the backend's ADMIN_TOKEN. It is kept in sessionStorage for this tab only.
 * There is no login in the demo: the token is the key to the seller's controls.
 */
export function AdminGate({ children }: { children: ReactNode }) {
  const [token, setToken] = useState("");
  const [draft, setDraft] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = getAdminToken();
    setToken(saved);
    setDraft(saved);
    setReady(true);
  }, []);

  if (!ready) return null;
  return (
    <div>
      <form
        className="mb-8 flex flex-wrap items-end gap-3 border-y border-ink py-3"
        onSubmit={(e) => {
          e.preventDefault();
          setAdminToken(draft.trim());
          setToken(draft.trim());
        }}
      >
        <label className="flex flex-col text-xs font-semibold uppercase text-mute">
          Admin token
          <input
            type="password"
            autoComplete="off"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="mt-1 min-h-11 w-72 max-w-full border-2 border-ink bg-paper px-3 font-mono text-sm normal-case text-ink"
          />
        </label>
        <Button type="submit" variant="secondary">
          {token ? "Update" : "Unlock"}
        </Button>
        <p className="text-xs text-mute">
          Kept for this tab only. Set as ADMIN_TOKEN on the backend.
        </p>
      </form>
      {token ? children : <p className="text-mute">Enter the admin token to load this screen.</p>}
    </div>
  );
}

export function ErrorLine({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className="my-3 border-l-4 border-signal pl-3 text-sm font-semibold text-signal"
    >
      {message}
    </p>
  );
}
