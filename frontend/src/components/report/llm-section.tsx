import { StatusTag } from "@/components/ui";
import { llm, llmRows, llmSummary } from "@/lib/llm-runs";

/**
 * Real language-model runs, shown next to (never inside) the scripted benchmark. One run per
 * task, AFTER mode only, so this is a spot check and not a statistic. Each row opens its raw run.
 */
export function LlmRuns() {
  const rows = llmRows();
  const s = llmSummary();
  return (
    <div>
      <p className="mt-2 max-w-2xl text-sm">
        <StatusTag kind="ok">Real model</StatusTag> <span data-static>{llm.requested_model}</span>{" "}
        through <span data-static>{llm.provider}</span>, temperature{" "}
        <span data-static>{llm.temperature}</span>, reading the store only through its MCP tools. It
        ran each of the <span data-static>{s.total}</span> tasks <span data-static>{llm.k}</span>{" "}
        time in AFTER mode. That is a spot check, not a statistic: it was not run in BEFORE mode and
        one run per task cannot show a rate. Recorded{" "}
        <span data-static>{llm.recorded_at.slice(0, 10)}</span>.
      </p>
      <p className="mt-3 font-mono text-sm font-bold">
        <span data-static>
          {s.ok}/{s.total}
        </span>{" "}
        met the expected outcome · <span data-static>{s.unsafe}</span> unsafe actions · average{" "}
        <span data-static>{s.avgSteps.toFixed(1)}</span> tool calls
      </p>
      <div className="relative mt-4 overflow-x-auto">
        <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
          <caption className="sr-only">Real language-model runs, one per task</caption>
          <thead>
            <tr className="border-b-2 border-ink font-mono text-xs uppercase">
              <th scope="col" className="py-2 pr-4">
                Task
              </th>
              <th scope="col" className="py-2 pr-4">
                Expected
              </th>
              <th scope="col" className="py-2 pr-4">
                Model ended with
              </th>
              <th scope="col" className="py-2 pr-4">
                Result
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-ink align-top">
                <th scope="row" className="py-2 pr-4 font-normal">
                  <span data-static>{r.title}</span>
                  <span data-static className="block font-mono text-xs text-mute">
                    {r.id} · {r.steps} calls · {r.seconds.toFixed(1)}s
                  </span>
                </th>
                <td data-static className="py-2 pr-4 font-mono text-xs">
                  {r.expected}
                </td>
                <td data-static className="py-2 pr-4 font-mono text-xs">
                  {r.got}
                </td>
                <td className="py-2 pr-4">
                  <details>
                    <summary className="cursor-pointer font-mono font-bold underline decoration-dotted underline-offset-4">
                      {r.ok ? "met" : "missed"}
                      <span className="sr-only"> (open the raw run)</span>
                    </summary>
                    <div className="mt-2 max-w-xl border border-ink bg-paper p-3 text-xs">
                      <p data-static className="font-mono">
                        {r.tools}
                      </p>
                      <pre
                        data-static
                        className="mt-2 max-h-64 overflow-auto bg-ink p-2 text-paper"
                      >
                        {JSON.stringify(r.raw, null, 2)}
                      </pre>
                    </div>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
