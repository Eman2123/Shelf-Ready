import type { ReactNode } from "react";

export function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="scroll-mt-6 border-t-4 border-ink pt-6">
      <h2 id={`${id}-h`} className="font-display text-3xl font-bold tracking-tight md:text-4xl">
        {title}
      </h2>
      <div className="mt-4 space-y-4 leading-relaxed">{children}</div>
    </section>
  );
}

export const H3 = ({ children }: { children: ReactNode }) => (
  <h3 className="pt-2 font-display text-xl font-bold">{children}</h3>
);

export function Code({ children, label }: { children: string; label?: string }) {
  return (
    <figure className="border-2 border-ink bg-ink text-paper">
      {label && (
        <figcaption className="border-b border-paper/30 px-3 py-1 font-mono text-xs uppercase text-hilite">
          {label}
        </figcaption>
      )}
      <pre className="overflow-x-auto p-3 font-mono text-sm leading-snug">
        <code>{children}</code>
      </pre>
    </figure>
  );
}

export function Ic({ children }: { children: ReactNode }) {
  return <code className="bg-hilite/60 px-1 font-mono text-[0.9em]">{children}</code>;
}

export function Table({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-x-auto border-2 border-ink">
      <table className="w-full min-w-[34rem] text-left text-sm">
        <thead className="bg-ink text-paper">
          <tr>
            {head.map((h) => (
              <th key={h} scope="col" className="px-3 py-2 font-mono text-xs uppercase">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-ink/40 align-top">
              {r.map((c, j) => (
                <td key={j} className="px-3 py-2">
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Note({ kind = "note", children }: { kind?: "note" | "warn"; children: ReactNode }) {
  return (
    <p
      className={`border-l-4 p-3 text-sm ${
        kind === "warn" ? "border-signal bg-signal/10" : "border-ink bg-hilite/50"
      }`}
    >
      <strong className="mr-1 font-mono text-xs uppercase">
        {kind === "warn" ? "Careful" : "Note"}
      </strong>
      {children}
    </p>
  );
}
