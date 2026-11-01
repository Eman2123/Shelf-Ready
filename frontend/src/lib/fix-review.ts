import type { FixProposal } from "@/lib/contracts";

export type Lane = "green" | "red" | "yellow";

const norm = (t: string) => t.replace(/\s+/g, " ").trim().toLowerCase();

/** Same rule as the backend fixture: a non-empty, case/space-insensitive quote of the source. */
export function snippetSupported(source: string, snippet: string): boolean {
  const s = norm(snippet);
  return s.length > 0 && norm(source).includes(s);
}

export function laneOf(fix: FixProposal): Lane {
  if (fix.status === "REJECTED") return "red";
  if (fix.status === "NEEDS_SELLER_INPUT") return "yellow";
  return "green"; // PROPOSED, APPROVED, APPLIED
}

/**
 * Header counter (PRD 4.2). Counts APPLIED fields in the catalog and how many of them are
 * backed by seller input or by a snippet that really exists in the source.
 */
export function unsupportedCounter(fixes: FixProposal[], source: string) {
  const applied = fixes.filter((f) => f.status === "APPLIED");
  const verified = applied.filter(
    (f) =>
      f.evidence !== null &&
      (f.evidence.method === "SELLER_INPUT" || snippetSupported(source, f.evidence.sourceSnippet)),
  );
  return {
    unsupported: applied.length - verified.length,
    verified: verified.length,
    total: applied.length,
  };
}

/** Split the source into before / match / after so the snippet can be highlighted. */
export function splitAtSnippet(source: string, snippet: string) {
  const s = snippet.replace(/\s+/g, " ").trim();
  if (!s) return null;
  const i = source.toLowerCase().indexOf(s.toLowerCase());
  if (i < 0) return null;
  return {
    before: source.slice(0, i),
    match: source.slice(i, i + s.length),
    after: source.slice(i + s.length),
  };
}
