import { createFileRoute } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Shell } from "../components/Shell";
import { useDevelopmentSummary } from "../queries/development";
import type { SeasonProgressionOut } from "../api/types";

const ProgressionRow = ({ p }: { p: SeasonProgressionOut }) => {
  const arrow = p.overall_after === p.overall_before ? "→" : p.overall_after > p.overall_before ? "↑" : "↓";
  const color =
    p.overall_after > p.overall_before
      ? "var(--green)"
      : p.overall_after < p.overall_before
      ? "var(--red)"
      : "var(--ink-3)";
  return (
    <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--line)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div style={{ fontWeight: 600 }}>{p.player_name}</div>
        <div style={{ fontSize: 12, color: "var(--ink-3)" }}>
          {p.player_type} · age {p.age_before} → {p.age_after} · POT {p.potential} · {p.development_type}
        </div>
      </div>
      <div style={{ fontFamily: "'Roboto Condensed', monospace", fontSize: 14, color }}>
        OVR {p.overall_before} {arrow} {p.overall_after}{" "}
        <span style={{ color: "var(--ink-3)", fontStyle: "italic" }}>({p.summary_reason})</span>
      </div>
      {p.events.length > 0 && (
        <div style={{ marginTop: 4, fontSize: 12, color: "var(--ink-2)", display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 4 }}>
          {p.events.map((e, i) => (
            <span key={i}>
              {e.attribute}: {e.old_value} → {e.new_value} ({e.delta > 0 ? "+" : ""}
              {e.delta})
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

const Page = () => {
  const { season_id } = Route.useSearch();
  const q = useDevelopmentSummary(season_id);
  if (q.isLoading || !q.data) {
    return <Shell crumbs={["Continental Hockey League", "Development"]}>Loading…</Shell>;
  }
  return (
    <Shell crumbs={["Continental Hockey League", "Development", `Season ${q.data.season_id}`]}>
      <Card title={`Player Development — Season ${q.data.season_id}`}>
        {q.data.progressions.map((p) => (
          <ProgressionRow key={`${p.player_type}-${p.player_id}`} p={p} />
        ))}
      </Card>
    </Shell>
  );
};

type SearchParams = { season_id?: number };

export const Route = createFileRoute("/development-summary")({
  component: Page,
  validateSearch: (search: Record<string, unknown>): SearchParams => {
    const v = search.season_id;
    if (v === undefined || v === null || v === "") return {};
    const n = typeof v === "number" ? v : Number(v);
    return Number.isFinite(n) ? { season_id: n } : {};
  },
});
