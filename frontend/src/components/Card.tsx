import type { ReactNode } from "react";
import { cn } from "../lib/cn";

export const Card = ({
  children,
  className,
  title,
  sub,
  link,
}: {
  children: ReactNode;
  className?: string;
  title?: ReactNode;
  sub?: ReactNode;
  link?: ReactNode;
}) => (
  <div className={cn("card", className)}>
    {(title || sub || link) && (
      <div className="card-h">
        {title && <span className="title">{title}</span>}
        {sub && <span className="sub">{sub}</span>}
        <span className="grow" />
        {link}
      </div>
    )}
    {children}
  </div>
);
