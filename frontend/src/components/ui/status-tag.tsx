import type { ReactNode } from "react";

export type StatusKind = "ok" | "blocked" | "wait";

const COLOR: Record<StatusKind, string> = {
  ok: "text-ok",
  blocked: "text-signal",
  wait: "text-wait",
};

const LABEL: Record<StatusKind, string> = {
  ok: "Verified",
  blocked: "Blocked",
  wait: "Waiting",
};

/** Status is always a word, never colour alone. */
export function StatusTag({ kind, children }: { kind: StatusKind; children?: ReactNode }) {
  return (
    <span className={`text-xs font-extrabold uppercase tracking-wider ${COLOR[kind]}`}>
      {children ?? LABEL[kind]}
    </span>
  );
}
