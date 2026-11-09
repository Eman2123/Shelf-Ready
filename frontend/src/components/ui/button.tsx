import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary";

const BASE =
  "min-h-11 px-6 text-sm font-extrabold uppercase tracking-wide disabled:cursor-not-allowed " +
  "disabled:border-2 disabled:border-dashed disabled:border-mute disabled:bg-paper " +
  "disabled:text-mute";

const VARIANT: Record<Variant, string> = {
  primary: "bg-ink text-paper hover:bg-signal",
  secondary: "border-2 border-ink bg-paper text-ink hover:bg-ink hover:text-paper",
};

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button type={type} className={`${BASE} ${VARIANT[variant]} ${className}`} {...rest} />;
}
