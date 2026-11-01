import { AgentTestView } from "@/components/agent-test/agent-test-view";

export const metadata = { title: "Agent test · ShelfReady" };

/** Agent test screen (owner: B). Split BEFORE / AFTER view of the same task. */
export default function AgentTestPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-bold">Agent test</h1>
      <p className="mt-1 mb-4 text-gray-700">
        The same buyer agent and the same task, before and after the store is made agent-ready.
        BEFORE never spends money: it records a purchase intent.
      </p>
      <AgentTestView />
    </main>
  );
}
