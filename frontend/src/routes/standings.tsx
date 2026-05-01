import { createFileRoute, Link } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Pagination, usePager } from "../components/Pagination";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { useAllGameplans } from "../queries/gameplan";
import { useLeague } from "../queries/league";
import { useStandings } from "../queries/standings";
import { useTeams } from "../queries/teams";

const StandingsPage = () => {
  const s = useStandings();
  const l = useLeague();
  const teams = useTeams();
  const gameplans = useAllGameplans();
  if (!s.data || !l.data || !teams.data) {
    return <Shell crumbs={["Continental Hockey League", "Standings"]}>Loading…</Shell>;
  }
  const gpByTeam = new Map(
    (gameplans.data?.rows ?? []).map((g) => [g.team_id, g]),
  );
  const userId = l.data.user_team_id;
  const playoffCut = Math.min(4, s.data.rows.length - 1);
  const pager = usePager(s.data.rows);

  return (
    <Shell crumbs={["Continental Hockey League", "Standings"]}>
      <div className="section-h">
        <h1>League Standings</h1>
        <span className="sub">
          {s.data.rows.reduce((a, r) => a + r.games_played, 0) / 2} games played · top{" "}
          {playoffCut + 1} qualify
        </span>
      </div>

      <Card>
        <Table>
          <thead>
            <tr>
              <Th style={{ width: 32 }}></Th>
              <Th>Team</Th>
              <Th className="num">GP</Th>
              <Th className="num">W</Th>
              <Th className="num">L</Th>
              <Th className="num">OTL</Th>
              <Th className="num">PTS</Th>
              <Th className="num">GF</Th>
              <Th className="num">GA</Th>
              <Th className="num">DIFF</Th>
              <Th className="num">PT%</Th>
              <Th>Style</Th>
              <Th>Lines</Th>
            </tr>
          </thead>
          <tbody>
            {pager.slice.map((r, i) => {
              const t = teams.data!.find((x) => x.id === r.team_id);
              if (!t) return null;
              const diff = r.goals_for - r.goals_against;
              const pct = r.games_played ? (r.points / (r.games_played * 2)).toFixed(3).slice(1) : "—";
              return (
                <tr key={r.team_id} className={r.team_id === userId ? "me" : ""}>
                  <Td className="rank">{pager.page * pager.pageSize + i + 1}</Td>
                  <Td>
                    <Link
                      to="/team/$teamId"
                      params={{ teamId: String(t.id) }}
                      style={{ color: "inherit", textDecoration: "none" }}
                    >
                      <span className="team-row">
                        <Logo teamId={t.id} size={22} />
                        <span className="nm">{t.name}</span>
                        <span className="ab">{t.abbreviation}</span>
                      </span>
                    </Link>
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
                  <Td className="num" style={{ color: diff >= 0 ? "var(--green)" : "var(--red)", fontWeight: 700 }}>
                    {diff > 0 ? "+" : ""}
                    {diff}
                  </Td>
                  <Td className="num">{pct}</Td>
                  <Td>
                    <span className="chip">{gpByTeam.get(r.team_id)?.style ?? "—"}</span>
                  </Td>
                  <Td>
                    <span className="chip">{gpByTeam.get(r.team_id)?.line_usage ?? "—"}</span>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
        <Pagination {...pager} onPage={pager.setPage} />
      </Card>
    </Shell>
  );
};

export const Route = createFileRoute("/standings")({ component: StandingsPage });
