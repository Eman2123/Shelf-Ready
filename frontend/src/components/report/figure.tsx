import { findRecord } from "@/lib/recorded";
import { makeFig, type Fig } from "@/lib/report";

/**
 * A number in the Report. It always carries its run ids and opens the raw record behind it.
 * Built on <details>, so it works from the keyboard and without JavaScript.
 */
export function Figure({ fig, big = false }: { fig: Fig; big?: boolean }) {
  const { text, runIds } = makeFig(fig.text, fig.runIds); // throws if a run id is missing
  const first = findRecord(runIds[0]);
  return (
    <details data-figure data-run-ids={runIds.join(",")} className="group">
      <summary
        className={`cursor-pointer font-mono font-bold underline decoration-dotted underline-offset-4 ${
          big ? "font-display text-5xl" : ""
        }`}
      >
        {text}
        <span className="sr-only"> (open the runs behind this number)</span>
      </summary>
      <div className="mt-2 max-w-xl border border-ink bg-paper p-3 text-xs font-normal">
        <p data-static className="font-mono">
          {runIds.length} run{runIds.length === 1 ? "" : "s"}:
        </p>
        <ul data-static className="mt-1 flex flex-wrap gap-x-3 font-mono">
          {runIds.map((id) => (
            <li key={id}>{id}</li>
          ))}
        </ul>
        <p className="mt-2 font-bold">Raw record of {runIds[0]}</p>
        <pre data-static className="mt-1 max-h-64 overflow-auto bg-ink p-2 text-paper">
          {JSON.stringify(first, null, 2)}
        </pre>
      </div>
    </details>
  );
}
