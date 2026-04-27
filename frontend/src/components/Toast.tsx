import type { ReactNode } from "react";

export const InlineError = ({ children }: { children: ReactNode }) => (
  <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded">{children}</div>
);
