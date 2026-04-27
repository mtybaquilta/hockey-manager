import type { ReactNode } from "react";
import { cn } from "../lib/cn";

export const Card = ({
  children,
  className,
  title,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
}) => (
  <div className={cn("rounded-lg border bg-white shadow-sm p-4", className)}>
    {title && <h3 className="font-semibold mb-2">{title}</h3>}
    {children}
  </div>
);
