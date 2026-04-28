import type { ButtonHTMLAttributes } from "react";
import { cn } from "../lib/cn";

type Variant = "primary" | "ghost" | "default";

export const Button = ({
  className,
  variant = "primary",
  ...p
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) => {
  const v = variant === "primary" ? "btn btn-primary" : variant === "ghost" ? "btn btn-ghost" : "btn";
  return <button {...p} className={cn(v, className)} />;
};
