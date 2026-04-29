import { useMemo, useState } from "react";

export const PAGE_SIZE = 50;

export function usePager<T>(items: T[], pageSize: number = PAGE_SIZE) {
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const safePage = Math.min(page, totalPages - 1);
  const slice = useMemo(
    () => items.slice(safePage * pageSize, safePage * pageSize + pageSize),
    [items, safePage, pageSize],
  );
  return {
    page: safePage,
    setPage,
    slice,
    total: items.length,
    totalPages,
    pageSize,
  };
}

export const Pagination = ({
  page,
  totalPages,
  total,
  pageSize,
  onPage,
}: {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPage: (p: number) => void;
}) => {
  if (total <= pageSize) return null;
  const start = page * pageSize + 1;
  const end = Math.min(total, (page + 1) * pageSize);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 14px",
        borderTop: "1px solid var(--line)",
        background: "var(--bone)",
        fontSize: 11,
        color: "var(--ink-3)",
        fontWeight: 600,
        letterSpacing: "0.04em",
      }}
    >
      <span>
        {start}–{end} of {total}
      </span>
      <div style={{ flex: 1 }} />
      <button
        className="btn btn-ghost"
        style={{ height: 26 }}
        disabled={page === 0}
        onClick={() => onPage(page - 1)}
      >
        ‹ Prev
      </button>
      <span style={{ fontFamily: "'Roboto Condensed', monospace", color: "var(--ink-2)" }}>
        Page {page + 1} / {totalPages}
      </span>
      <button
        className="btn btn-ghost"
        style={{ height: 26 }}
        disabled={page >= totalPages - 1}
        onClick={() => onPage(page + 1)}
      >
        Next ›
      </button>
    </div>
  );
};
