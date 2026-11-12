import type { ReactNode, SVGProps } from "react";

/** Line icons, 24px grid, drawn with currentColor so they follow text colour. Decorative by default. */
function Svg({ children, ...props }: SVGProps<SVGSVGElement> & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="square"
      strokeLinejoin="miter"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

const PATHS = {
  /** plug: connect a store */
  connect: (
    <>
      <path d="M9 3v5M15 3v5" />
      <path d="M6 8h12v4a6 6 0 0 1-12 0V8Z" />
      <path d="M12 18v3" />
    </>
  ),
  /** magnifier over lines: audit */
  audit: (
    <>
      <circle cx="10.5" cy="10.5" r="6" />
      <path d="m15 15 6 6" />
      <path d="M8 10.5h5M8 13h3" />
    </>
  ),
  /** check inside a document: fix review */
  fix: (
    <>
      <path d="M6 3h9l4 4v14H6V3Z" />
      <path d="M15 3v4h4" />
      <path d="m9 14 2.5 2.5L16 12" />
    </>
  ),
  /** robot head: agent test */
  agent: (
    <>
      <rect x="4" y="8" width="16" height="12" />
      <path d="M12 8V4M9 4h6" />
      <circle cx="9" cy="14" r="1.2" />
      <circle cx="15" cy="14" r="1.2" />
    </>
  ),
  key: (
    <>
      <circle cx="8" cy="14" r="4" />
      <path d="m11 11 9-9M16 6l3 3M14 8l2 2" />
    </>
  ),
  /** receipt: orders */
  orders: (
    <>
      <path d="M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2V3Z" />
      <path d="M9 8h6M9 12h6" />
    </>
  ),
  /** bars: report */
  report: (
    <>
      <path d="M4 20h16" />
      <path d="M7 20v-7M12 20V6M17 20v-10" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="11" width="14" height="10" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  scale: (
    <>
      <path d="M12 4v16M7 20h10" />
      <path d="M4 8h16" />
      <path
        d="m4 8-2 6a3 3 0 0 0 6 0L4 8ZM20 8l-2 6a3 3 0 0 0 6 0l-4-6Z"
        transform="translate(-1 0)"
      />
    </>
  ),
  webhook: (
    <>
      <path d="M13 3 5 13h6l-1 8 8-10h-6l1-8Z" />
    </>
  ),
  refund: (
    <>
      <path d="M4 12a8 8 0 1 1 3 6.2" />
      <path d="M4 18v-6h6" />
    </>
  ),
  code: <path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16" />,
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  eye: (
    <>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  block: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m6 6 12 12" />
    </>
  ),
  flask: (
    <>
      <path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3" />
      <path d="M7.500 15h9" />
    </>
  ),
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof PATHS;

export function Icon({
  name,
  size = 24,
  className,
}: {
  name: IconName;
  size?: number;
  className?: string;
}) {
  return (
    <Svg width={size} height={size} className={className}>
      {PATHS[name]}
    </Svg>
  );
}
