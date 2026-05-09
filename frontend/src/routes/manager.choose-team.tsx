import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Logo } from "../components/Logo";
import { Shell } from "../components/Shell";
import { attrClass } from "../lib/team-colors";
import { useSelectOverview, useSetManagerTeam } from "../queries/manager";
import type { TeamSelectOverview } from "../api/types";

const difficultyChip = (d: TeamSelectOverview["difficulty"]) => {
  if (d === "easy") return { label: "Easy", color: "#15803d", bg: "rgba(34, 197, 94, 0.15)" };
  if (d === "hard") return { label: "Hard", color: "#b91c1c", bg: "rgba(220, 38, 38, 0.15)" };
  return { label: "Medium", color: "#b45309", bg: "rgba(245, 158, 11, 0.15)" };
};

const ChooseTeam = () => {
  const overview = useSelectOverview();
  const setTeam = useSetManagerTeam();
  const nav = useNavigate();

  if (!overview.data) {
    return <Shell crumbs={["Choose Your Team"]}>Loading…</Shell>;
  }

  const onPick = (teamId: number) => {
    setTeam.mutate(teamId, { onSuccess: () => nav({ to: "/" }) });
  };

  return (
    <Shell crumbs={["Choose Your Team"]}>
      <div className="section-h">
        <h1>Pick a team to manage</h1>
        <span className="sub">{overview.data.length} teams</span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 14,
        }}
      >
        {overview.data.map((t) => {
          const diff = difficultyChip(t.difficulty);
          return (
            <div
              key={t.id}
              className="card"
              style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <Logo teamId={t.id} size={40} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>{t.name}</div>
                  <div style={{ fontSize: 11, color: "var(--ink-3)" }}>{t.abbreviation}</div>
                </div>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "3px 8px",
                    borderRadius: 4,
                    color: diff.color,
                    background: diff.bg,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                  }}
                >
                  {diff.label}
                </span>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span className={`chip ovr ${attrClass(t.team_ovr)}`}>{t.team_ovr} OVR</span>
                <span className="chip" style={{ fontSize: 11 }}>{t.style}</span>
                <span className="chip" style={{ fontSize: 11 }}>{t.line_usage}</span>
              </div>
              {t.best_player && (
                <div style={{ fontSize: 12, color: "var(--ink-2)" }}>
                  <span style={{ color: "var(--ink-3)" }}>Best: </span>
                  {t.best_player.name} ({t.best_player.position}) — {t.best_player.ovr} OVR
                </div>
              )}
              {t.best_prospect && (
                <div style={{ fontSize: 12, color: "var(--ink-2)" }}>
                  <span style={{ color: "var(--ink-3)" }}>Prospect: </span>
                  {t.best_prospect.name} ({t.best_prospect.position}) — {t.best_prospect.ovr}/{t.best_prospect.potential}
                </div>
              )}
              <button
                className="btn btn-primary"
                disabled={setTeam.isPending}
                onClick={() => onPick(t.id)}
                style={{ marginTop: "auto" }}
              >
                {setTeam.isPending ? "Selecting…" : "Manage this team"}
              </button>
            </div>
          );
        })}
      </div>
    </Shell>
  );
};

export const Route = createFileRoute("/manager/choose-team")({ component: ChooseTeam });
