import { AdminGate } from "@/components/admin/use-admin";
import { KeysView } from "@/components/admin/keys-view";

export const metadata = { title: "Agent keys · ShelfReady" };

export default function Page() {
  return (
    <div>
      <h1 className="font-display text-6xl font-bold leading-none tracking-tight">Agent keys</h1>
      <p className="mt-3 mb-6 max-w-2xl">
        One key per agent, with scopes, a per-order limit and a daily budget. The raw key is shown
        once. Revoking takes effect on the agent&apos;s next request.
      </p>
      <AdminGate>
        <KeysView />
      </AdminGate>
    </div>
  );
}
