import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Pagination, usePager } from "../components/Pagination";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { useAllGameplans } from "../queries/gameplan";
import { useGoalieStats, useSkaterStats, useTeamStats } from "../queries/stats";
import { useTeams } from "../queries/teams";

type Tab = "skaters" | "goalies" | "teams";

const pct = (v: number) => (v ? `${(v * 100).toFixed(1)}%` : "—");
const dec3 = (v: number) => (v ? v.toFixed(3).replace(/^0/, "") : "—");

const StatsPage = () => {
  const [tab, setTab] = useState<Tab>("skaters");
  return (
    <Shell crumbs={["Continental Hockey League", "Stats"]}>
      <div className="section-h">
        <h1>Stats Hub</h1>
        <span className="sub">League leaders &amp; full season aggregates</span>
      </div>
      <div className="tabs">
        {(["skaters", "goalies", "teams"] as Tab[]).map((t) => (
          <a key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)} style={{ textTransform: "capitalize" }}>
            {t}
          </a>
        ))}
      </div>
      {tab === "skaters" && <SkatersTab />}
      {tab === "goalies" && <GoaliesTab />}
      {tab === "teams" && <TeamsTab />}
    </Shell>
  );
};

const SkatersTab = () => {
  const q = useSkaterStats();
  const pager = usePager(q.data?.rows ?? []);
  if (!q.data) return <Card>Loading…</Card>;
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <Th></Th>
            <Th>Player</Th>
            <Th>Team</Th>
            <Th>Pos</Th>
            <Th className="num">GP</Th>
            <Th className="num">G</Th>
            <Th className="num">A</Th>
            <Th className="num">PTS</Th>
            <Th className="num">SOG</Th>
            <Th className="num">SH%</Th>
          </tr>
        </thead>
        <tbody>
          {pager.slice.map((r, i) => (
            <tr key={r.skater_id}>
              <Td className="rank">{pager.page * pager.pageSize + i + 1}</Td>
              <Td>
                <Link to="/player/skater/$id" params={{ id: String(r.skater_id) }} className="link" style={{ fontWeight: 700, color: "var(--ink)" }}>
                  {r.name}
                </Link>
              </Td>
              <Td>
                <TeamCell teamId={r.team_id} />
              </Td>
              <Td style={{ color: "var(--ink-3)" }}>{r.position}</Td>
              <Td className="num">{r.games_played}</Td>
              <Td className="num">{r.goals}</Td>
              <Td className="num">{r.assists}</Td>
              <Td className="num">
                <b>{r.points}</b>
              </Td>
              <Td className="num">{r.shots}</Td>
              <Td className="num">{pct(r.shooting_pct)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
      <Pagination {...pager} onPage={pager.setPage} />
    </Card>
  );
};

const GoaliesTab = () => {
  const q = useGoalieStats();
  const pager = usePager(q.data?.rows ?? []);
  if (!q.data) return <Card>Loading…</Card>;
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <Th></Th>
            <Th>Goalie</Th>
            <Th>Team</Th>
            <Th className="num">GP</Th>
            <Th className="num">SA</Th>
            <Th className="num">SV</Th>
            <Th className="num">GA</Th>
            <Th className="num">SV%</Th>
            <Th className="num">GAA</Th>
          </tr>
        </thead>
        <tbody>
          {pager.slice.map((r, i) => (
            <tr key={r.goalie_id}>
              <Td className="rank">{pager.page * pager.pageSize + i + 1}</Td>
              <Td>
                <Link to="/player/goalie/$id" params={{ id: String(r.goalie_id) }} className="link" style={{ fontWeight: 700, color: "var(--ink)" }}>
                  {r.name}
                </Link>
              </Td>
              <Td>
                <TeamCell teamId={r.team_id} />
              </Td>
              <Td className="num">{r.games_played}</Td>
              <Td className="num">{r.shots_against}</Td>
              <Td className="num">{r.saves}</Td>
              <Td className="num">{r.goals_against}</Td>
              <Td className="num">
                <b>{dec3(r.save_pct)}</b>
              </Td>
              <Td className="num">{r.gaa.toFixed(2)}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
      <Pagination {...pager} onPage={pager.setPage} />
    </Card>
  );
};

const TeamsTab = () => {
  const q = useTeamStats();
  const gameplans = useAllGameplans();
  const pager = usePager(q.data?.rows ?? []);
  if (!q.data) return <Card>Loading…</Card>;
  const gpByTeam = new Map(
    (gameplans.data?.rows ?? []).map((g) => [g.team_id, g]),
  );
  return (
    <Card>
      <Table>
        <thead>
          <tr>
            <Th></Th>
            <Th>Team</Th>
            <Th className="num">GP</Th>
            <Th className="num">W</Th>
            <Th className="num">L</Th>
            <Th className="num">OTL</Th>
            <Th className="num">PTS</Th>
            <Th className="num">GF</Th>
            <Th className="num">GA</Th>
            <Th className="num">DIFF</Th>
            <Th className="num">G/G</Th>
            <Th className="num">S/G</Th>
            <Th className="num">SV%</Th>
            <Th className="num">SH%</Th>
            <Th className="num">PP%</Th>
            <Th className="num">PK%</Th>
            <Th>Style</Th>
            <Th>Lines</Th>
          </tr>
        </thead>
        <tbody>
          {pager.slice.map((r, i) => (
            <tr key={r.team_id}>
              <Td className="rank">{pager.page * pager.pageSize + i + 1}</Td>
              <Td>
                <TeamCell teamId={r.team_id} fullName />
              </Td>
              <Td className="num">{r.games_played}</Td>
              <Td className="num">{r.wins}</Td>
              <Td className="num">{r.losses}</Td>
              <Td className="num">{r.ot_losses}</Td>
              <Td className="num">
                <b>{r.points}</b>
              </Td>
              <Td className="num">{r.goals_for}</Td>
              <Td className="num">{r.goals_against}</Td>
              <Td className="num" style={{ color: r.diff >= 0 ? "var(--green)" : "var(--red)", fontWeight: 700 }}>
                {r.diff > 0 ? "+" : ""}
                {r.diff}
              </Td>
              <Td className="num">{r.goals_per_game.toFixed(2)}</Td>
              <Td className="num">{r.shots_per_game.toFixed(1)}</Td>
              <Td className="num">{dec3(r.save_pct)}</Td>
              <Td className="num">{pct(r.shooting_pct)}</Td>
              <Td className="num">{pct(r.pp_pct)}</Td>
              <Td className="num">{pct(r.pk_pct)}</Td>
              <Td>
                <span className="chip">{gpByTeam.get(r.team_id)?.style ?? "—"}</span>
              </Td>
              <Td>
                <span className="chip">{gpByTeam.get(r.team_id)?.line_usage ?? "—"}</span>
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>
      <Pagination {...pager} onPage={pager.setPage} />
    </Card>
  );
};

const TeamCell = ({ teamId, fullName = false }: { teamId: number; fullName?: boolean }) => {
  const teams = useTeams();
  const t = teams.data?.find((x) => x.id === teamId);
  if (!t) return <span>—</span>;
  return (
    <Link
      to="/team/$teamId"
      params={{ teamId: String(teamId) }}
      style={{ color: "inherit", textDecoration: "none" }}
    >
      <span className="team-row">
        <Logo teamId={teamId} size={18} />
        <span className="nm">{fullName ? t.name : t.abbreviation}</span>
      </span>
    </Link>
  );
};

export const Route = createFileRoute("/stats")({ component: StatsPage });
