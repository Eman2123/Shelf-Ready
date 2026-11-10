"use client";

import { useEffect, useState } from "react";
import { Button, StatusTag, type StatusKind } from "@/components/ui";
import type { AgentRun } from "@/lib/contracts";
import { recorded, runsFor, totals } from "@/lib/recorded";

type RecordedRun = AgentRun;

const OUTCOME_KIND: Record<RecordedRun["outcome"], StatusKind> = {
  SUCCESS: "ok",
  FAILED: "blocked",
  WRONG_RESULT: "blocked",
  POLICY_VIOLATION: "blocked",
};

const fmt = (n: number) => n.toLocaleString("en-US");
const MAX_SHOWN = 400;
/** One-line view of a tool input or output; the full record is in the Report's raw record. */
const show = (v: unknown) => {
  const text = typeof v === "string" ? v : JSON.stringify(v);
  return text.length > MAX_SHOWN
    ? `${text.slice(0, MAX_SHOWN)}… (${fmt(text.length)} chars)`
    : text;
};
/** Scripted agents finish in under a millisecond, so say that instead of a fake "0.0 s". */
const fmtDuration = (ms: number) => (ms < 1 ? "< 1 ms" : `${fmt(ms)} ms`);

function Lane({ run, visible }: { run: RecordedRun; visible: number }) {
  const t = totals(run);
  const kn = recorded.metrics[run.mode].perTask[run.taskId];
  const done = visible >= run.steps.length;
  const before = run.mode === "BEFORE";
  return (
    <section
      aria-label={`${run.mode} run`}
      className={`min-w-0 border-t-8 pt-4 ${before ? "border-signal" : "border-ok"}`}
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-4xl font-bold tracking-tight">
          {before ? "Before" : "After"}
          <span className="ml-3 text-sm font-normal normal-case tracking-normal text-mute">
            {before ? "reads the web page" : "uses the store MCP"}
          </span>
        </h2>
        {done && <StatusTag kind={OUTCOME_KIND[run.outcome]}>{run.outcome}</StatusTag>}
      </header>
      <p className="mt-1 font-mono text-xs text-mute">
        {kn.success}/{kn.runs} runs succeeded · {run.id}
      </p>

      <dl className="mt-4 grid grid-cols-3 border-y border-ink text-sm">
        <div className="border-r border-ink py-2 pr-3">
          <dt className="text-xs font-semibold uppercase text-mute">Tool calls</dt>
          <dd className="font-mono text-2xl font-bold">{done ? t.toolCalls : visible}</dd>
        </div>
        <div className="border-r border-ink px-3 py-2">
          <dt className="text-xs font-semibold uppercase text-mute">HTML bytes</dt>
          <dd className="font-mono text-2xl font-bold">
            {fmt(run.steps.slice(0, visible).reduce((s, x) => s + x.htmlBytes, 0))}
          </dd>
        </div>
        <div className="py-2 pl-3">
          <dt className="text-xs font-semibold uppercase text-mute">Duration</dt>
          <dd className="font-mono text-2xl font-bold">
            {done ? fmtDuration(run.durationMs) : "…"}
          </dd>
        </div>
      </dl>

      <ol className="mt-4 space-y-2" aria-live="polite">
        {run.steps.slice(0, visible).map((s) => (
          <li key={s.index} className="border border-ink p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono font-bold">
                {s.index + 1}. {s.tool}
              </span>
              <StatusTag kind={s.ok ? "ok" : "blocked"}>{s.ok ? "ok" : "unsafe"}</StatusTag>
            </div>
            <p className="mt-1 break-words font-mono text-xs text-mute">in: {show(s.input)}</p>
            <p className="mt-1 break-words text-xs">out: {show(s.output)}</p>
            {s.htmlBytes > 0 && (
              <p className="mt-1 text-xs text-mute">HTML read: {fmt(s.htmlBytes)} bytes</p>
            )}
          </li>
        ))}
      </ol>

      {done && run.failReason && (
        <p className="mt-3 bg-ink p-3 text-sm font-semibold text-paper">
          Why it failed: {run.failReason}
        </p>
      )}
    </section>
  );
}

export function AgentTestView() {
  const [taskId, setTaskId] = useState(recorded.tasks[0].id);
  const [tick, setTick] = useState(0);
  const [replayKey, setReplayKey] = useState(0);
  const [reduce, setReduce] = useState(false);
  const task = recorded.tasks.find((x) => x.id === taskId) ?? recorded.tasks[0];
  // replica 1 is shown as the trace; the k/3 line under each lane counts all replicas
  const runs = {
    BEFORE: runsFor(task.id, "BEFORE")[0].run,
    AFTER: runsFor(task.id, "AFTER")[0].run,
  };
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
      <p className="border-y border-ink py-3 text-sm">
        <span className="font-bold">Recorded runs.</span> {recorded.k} runs per task and mode by{" "}
        {recorded.agentConfigs.join(" and ")}. These are scripted baseline agents, not a language
        model, so each repeat gives the same result. Replay shows the stored trace; nothing is
        re-run.{" "}
        <span className="font-mono text-xs">sha256 {recorded.sourceSha256.slice(0, 12)}</span>
      </p>

      <div className="mt-5 flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-sm font-semibold" htmlFor="task">
          Task
          <select
            id="task"
            className="mt-1 min-h-11 border-2 border-ink bg-paper px-3 font-normal"
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
          >
            {recorded.tasks.map((x) => (
              <option key={x.id} value={x.id}>
                {x.title}
              </option>
            ))}
          </select>
        </label>
        <Button variant="secondary" onClick={() => setReplayKey((k) => k + 1)}>
          Replay
        </Button>
        <Button disabled title="Run `make bench-run` in the backend to record a new set">
          Run benchmark (script only)
        </Button>
      </div>

      <section aria-label="Task" className="mt-6 bg-ink p-5 text-paper">
        <p className="font-mono text-xs font-bold uppercase">Same task in both modes</p>
        <p className="font-display mt-2 text-3xl font-bold leading-tight">{task.prompt}</p>
        <p className="mt-3 text-sm">
          Expected: <span className="font-mono font-bold">{task.expected}</span> ·{" "}
          {task.successCriteria}
        </p>
      </section>

      <div className="mt-8 grid gap-10 md:grid-cols-2">
        <Lane run={runs.BEFORE} visible={Math.min(visible, runs.BEFORE.steps.length)} />
        <Lane run={runs.AFTER} visible={Math.min(visible, runs.AFTER.steps.length)} />
      </div>
    </div>
  );
}
