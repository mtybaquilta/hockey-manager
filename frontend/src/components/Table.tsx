import type { ReactNode, TdHTMLAttributes } from "react";
import { cn } from "../lib/cn";

export const Table = ({ children, className }: { children: ReactNode; className?: string }) => (
  <table className={cn("w-full text-sm", className)}>{children}</table>
);

export const Th = ({ children, className }: { children: ReactNode; className?: string }) => (
  <th className={cn("text-left font-medium px-2 py-1 border-b", className)}>{children}</th>
);

export const Td = ({ children, className, ...p }: TdHTMLAttributes<HTMLTableCellElement> & { children?: ReactNode }) => (
  <td {...p} className={cn("px-2 py-1 border-b", className)}>
    {children}
  </td>
);
