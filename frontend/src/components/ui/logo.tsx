import Link from "next/link";

/** Shelf mark (three items on a shelf). Same drawing as app/icon.svg. */
export function LogoMark({ size = 32 }: { size?: number }) {
  return (
    <svg viewBox="0 0 32 32" width={size} height={size} aria-hidden="true" focusable="false">
      <rect width="32" height="32" fill="#1b1a17" />
      <rect x="6" y="12" width="6" height="10" fill="#f2d68a" />
      <rect x="13" y="7" width="6" height="15" fill="#f7f1e3" />
      <rect x="20" y="15" width="6" height="7" fill="#b3261e" />
      <rect x="4" y="23" width="24" height="3" fill="#f7f1e3" />
    </svg>
  );
}

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2.5" aria-label="Shelf Ready home">
      <LogoMark />
      <span className="font-display text-2xl font-bold tracking-tight">Shelf Ready</span>
    </Link>
  );
}
