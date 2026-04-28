import type { ReactNode, TdHTMLAttributes, ThHTMLAttributes } from "react";
import { cn } from "../lib/cn";

export const Table = ({ children, className }: { children: ReactNode; className?: string }) => (
  <table className={cn("tbl", className)}>{children}</table>
);

export const Th = ({ children, className, ...p }: ThHTMLAttributes<HTMLTableCellElement> & { children?: ReactNode }) => (
  <th {...p} className={className}>
    {children}
  </th>
);

export const Td = ({ children, className, ...p }: TdHTMLAttributes<HTMLTableCellElement> & { children?: ReactNode }) => (
  <td {...p} className={className}>
    {children}
  </td>
);
