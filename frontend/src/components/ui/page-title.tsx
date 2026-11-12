import type { ReactNode } from "react";
import { Icon, type IconName } from "./icons";

/** Screen heading: icon in a ruled square, then the title. */
export function PageTitle({ icon, children }: { icon: IconName; children: ReactNode }) {
  return (
    <div className="flex items-center gap-4">
      <span className="flex h-14 w-14 shrink-0 items-center justify-center border-2 border-ink bg-hilite">
        <Icon name={icon} size={32} />
      </span>
      <h1 className="font-display text-5xl font-bold leading-none tracking-tight md:text-6xl">
        {children}
      </h1>
    </div>
  );
}
