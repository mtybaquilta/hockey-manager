import { createFileRoute, Link } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Shell } from "../components/Shell";
import { useLeague } from "../queries/league";
import { useManagerProfile } from "../queries/manager";
import { useTeams } from "../queries/teams";

const ManagerPage = () => {
  const profile = useManagerProfile();
  const teams = useTeams();
  const league = useLeague();

  if (!profile.data) {
    return (
      <Shell crumbs={["Manager"]}>
        <div className="card" style={{ padding: 20 }}>
          <p style={{ marginBottom: 12 }}>You haven't created a manager profile yet.</p>
          <Link to="/manager/create" className="btn btn-primary">
            Create manager →
          </Link>
        </div>
      </Shell>
    );
  }

  const p = profile.data;
  const team =
    p.current_team_id != null && teams.data
      ? teams.data.find((t) => t.id === p.current_team_id)
      : undefined;

  return (
    <Shell crumbs={["Manager"]}>
      <div className="section-h">
        <h1>{p.name}</h1>
        <span className="sub">
          {team ? `${team.name} · Year ${league.data?.year ?? "—"}` : "No team selected"}
        </span>
        <div style={{ flex: 1 }} />
        <Link to="/manager/choose-team" className="btn">
          Change team
        </Link>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
        <Card title="Career Record">
          <div style={{ padding: "14px 16px", display: "flex", gap: 22 }}>
            <Stat k="Wins" v={p.career_wins} />
            <Stat k="Losses" v={p.career_losses} />
            <Stat k="OT Losses" v={p.career_ot_losses} />
          </div>
        </Card>
        <Card title="Trophies">
          <div style={{ padding: "14px 16px", display: "flex", gap: 22 }}>
            <Stat k="Seasons" v={p.seasons_completed} />
            <Stat k="Championships" v={p.championships_won} />
          </div>
        </Card>
      </div>

      {team && (
        <Card title="Current Team">
          <div style={{ padding: "14px 16px", display: "flex", alignItems: "center", gap: 14 }}>
            <Logo teamId={team.id} size={48} />
            <div>
              <div style={{ fontWeight: 700 }}>{team.name}</div>
              <div style={{ color: "var(--ink-3)", fontSize: 12 }}>{team.abbreviation}</div>
            </div>
            <div style={{ flex: 1 }} />
            <Link to="/team/$teamId" params={{ teamId: String(team.id) }} className="btn">
              View roster →
            </Link>
          </div>
        </Card>
      )}
    </Shell>
  );
};

const Stat = ({ k, v }: { k: string; v: number | string }) => (
  <div>
    <div style={{ fontSize: 11, textTransform: "uppercase", color: "var(--ink-3)", letterSpacing: "0.06em" }}>
      {k}
    </div>
    <div style={{ fontSize: 22, fontWeight: 700 }}>{v}</div>
  </div>
);

export const Route = createFileRoute("/manager/")({ component: ManagerPage });
