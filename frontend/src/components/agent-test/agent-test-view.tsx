"use client";

import { useEffect, useState } from "react";
import { sampleRuns, sampleTasks, totals, type RecordedRun } from "@/lib/fixtures/agent-runs";

const OUTCOME_STYLE: Record<RecordedRun["outcome"], string> = {
  SUCCESS: "bg-green-100 text-green-900",
  FAILED: "bg-red-100 text-red-900",
  WRONG_RESULT: "bg-red-100 text-red-900",
  POLICY_VIOLATION: "bg-red-100 text-red-900",
};

const fmt = (n: number) => n.toLocaleString("en-US");
const show = (v: unknown) => (typeof v === "string" ? v : JSON.stringify(v));

function Lane({ run, visible }: { run: RecordedRun; visible: number }) {
  const t = totals(run);
  const done = visible >= run.steps.length;
  return (
    <section
      aria-label={`${run.mode} run`}
      className={`rounded border p-4 ${run.mode === "BEFORE" ? "border-red-300" : "border-green-400"}`}
    >
      <header className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">
          {run.mode === "BEFORE" ? "BEFORE · reads the web page" : "AFTER · uses the store MCP"}
        </h2>
        {done && (
          <span className={`rounded px-2 py-0.5 text-sm font-medium ${OUTCOME_STYLE[run.outcome]}`}>
            {run.outcome}
          </span>
        )}
      </header>

      <dl className="mt-3 grid grid-cols-3 gap-2 text-sm">
        <div>
          <dt className="text-gray-600">Tool calls</dt>
          <dd className="font-mono text-base">{done ? t.toolCalls : visible}</dd>
        </div>
        <div>
          <dt className="text-gray-600">HTML bytes read</dt>
          <dd className="font-mono text-base">
            {fmt(run.steps.slice(0, visible).reduce((s, x) => s + x.htmlBytes, 0))}
          </dd>
        </div>
        <div>
          <dt className="text-gray-600">Duration</dt>
          <dd className="font-mono text-base">
            {done ? `${(run.durationMs / 1000).toFixed(1)} s` : "…"}
          </dd>
        </div>
      </dl>

      <ol className="mt-4 space-y-2" aria-live="polite">
        {run.steps.slice(0, visible).map((s) => (
          <li key={s.index} className="rounded border bg-gray-50 p-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-mono font-semibold">
                {s.index + 1}. {s.tool}
              </span>
              <span className={s.ok ? "text-green-800" : "text-red-800"}>
                {s.ok ? "ok" : "unsafe"}
              </span>
            </div>
            <p className="mt-1 break-words font-mono text-xs text-gray-700">in: {show(s.input)}</p>
            <p className="mt-1 break-words text-xs">out: {show(s.output)}</p>
            {s.htmlBytes > 0 && (
              <p className="mt-1 text-xs text-gray-600">HTML read: {fmt(s.htmlBytes)} bytes</p>
            )}
          </li>
        ))}
      </ol>

      {done && run.failReason && (
        <p className="mt-3 rounded bg-red-50 p-2 text-sm text-red-900">
          Why it failed: {run.failReason}
        </p>
      )}
    </section>
  );
}

export function AgentTestView() {
  const [taskId, setTaskId] = useState(sampleTasks[0].id);
  const [tick, setTick] = useState(0);
  const [replayKey, setReplayKey] = useState(0);
  const [reduce, setReduce] = useState(false);
  const task = sampleTasks.find((x) => x.id === taskId) ?? sampleTasks[0];
  const runs = sampleRuns[task.id];
  const max = Math.max(runs.BEFORE.steps.length, runs.AFTER.steps.length);

  useEffect(() => {
    setReduce(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, []);

  useEffect(() => {
    if (reduce) return;
    setTick(0);
    const id = setInterval(() => setTick((t) => (t >= max ? t : t + 1)), 700);
    return () => clearInterval(id);
  }, [taskId, max, reduce, replayKey]);

  const visible = reduce ? max : tick;

  return (
    <div>
      <p className="rounded border border-yellow-400 bg-yellow-50 p-3 text-sm">
        Sample data. These runs are hand-written fixtures that show the layout. Real benchmark runs
        (k/3, model and version recorded) replace them when the runner is connected.
      </p>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-sm" htmlFor="task">
          Task
          <select
            id="task"
            className="mt-1 rounded border p-2"
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
          >
            {sampleTasks.map((x) => (
              <option key={x.id} value={x.id}>
                {x.title}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="rounded bg-blue-900 px-3 py-2 text-sm text-white"
          onClick={() => setReplayKey((k) => k + 1)}
        >
          Replay
        </button>
        <button
          type="button"
          disabled
          title="The benchmark runner is not connected yet"
          className="rounded border px-3 py-2 text-sm text-gray-500"
        >
          Run benchmark (not connected)
        </button>
      </div>

      <div className="mt-4 rounded border p-3 text-sm">
        <p>
          <span className="font-semibold">Same task in both modes:</span> {task.prompt}
        </p>
        <p className="mt-1 text-gray-700">
          Expected: <span className="font-mono">{task.expected}</span> · {task.successCriteria}
        </p>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Lane run={runs.BEFORE} visible={Math.min(visible, runs.BEFORE.steps.length)} />
        <Lane run={runs.AFTER} visible={Math.min(visible, runs.AFTER.steps.length)} />
      </div>
    </div>
  );
}
