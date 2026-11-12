import { PageTitle } from "@/components/ui";
import { AgentTestView } from "@/components/agent-test/agent-test-view";

export const metadata = { title: "Agent test · ShelfReady" };

/** Agent test screen (owner: B). Split BEFORE / AFTER view of the same task. */
export default function AgentTestPage() {
  return (
    <div>
      <PageTitle icon="agent">Agent test</PageTitle>
      <p className="mt-3 mb-6 max-w-2xl">
        The same buyer agent and the same task, before and after the store is made agent-ready.
        BEFORE never spends money: it records a purchase intent.
      </p>
      <AgentTestView />
    </div>
  );
}
