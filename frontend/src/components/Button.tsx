import type { ButtonHTMLAttributes } from "react";
import { cn } from "../lib/cn";

export const Button = ({ className, ...p }: ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button
    {...p}
    className={cn(
      "px-4 py-2 rounded bg-slate-900 text-white text-sm font-medium",
      "hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed",
      className,
    )}
  />
);
