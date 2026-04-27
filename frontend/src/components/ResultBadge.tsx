import type { ResultType } from "../api/types";
import { cn } from "../lib/cn";

export const ResultBadge = ({ type }: { type: ResultType | null }) => {
  if (!type || type === "REG") return null;
  return (
    <span
      className={cn(
        "inline-block px-1.5 py-0.5 rounded text-xs",
        type === "OT" ? "bg-amber-100 text-amber-800" : "bg-purple-100 text-purple-800",
      )}
    >
      {type}
    </span>
  );
};
