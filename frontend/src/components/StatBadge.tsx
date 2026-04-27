import type { ReactNode } from "react";

export const StatBadge = ({ label, value }: { label: string; value: ReactNode }) => (
  <div className="flex flex-col items-center px-3">
    <span className="text-xs text-slate-500">{label}</span>
    <span className="text-lg font-semibold">{value}</span>
  </div>
);
