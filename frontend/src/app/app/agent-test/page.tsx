import { AgentTestView } from "@/components/agent-test/agent-test-view";

export const metadata = { title: "Agent test · ShelfReady" };

/** Agent test screen (owner: B). Split BEFORE / AFTER view of the same task. */
export default function AgentTestPage() {
  return (
    <div>
      <h1 className="font-display text-6xl font-bold leading-none tracking-tight">Agent test</h1>
      <p className="mt-3 mb-6 max-w-2xl">
        The same buyer agent and the same task, before and after the store is made agent-ready.
        BEFORE never spends money: it records a purchase intent.
      </p>
      <AgentTestView />
    </div>
  );
}
