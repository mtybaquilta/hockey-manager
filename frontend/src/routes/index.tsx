import { createFileRoute, Link } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { ResultBadge } from "../components/ResultBadge";
import { Table, Td, Th } from "../components/Table";
import { TeamBadge } from "../components/TeamBadge";
import { useLeague } from "../queries/league";
import { useSchedule } from "../queries/schedule";
import { useStandings } from "../queries/standings";
import { useTeams } from "../queries/teams";

const Dashboard = () => {
  const league = useLeague();
  const schedule = useSchedule();
  const standings = useStandings();
  const teams = useTeams();
  if (!league.data || !schedule.data || !standings.data || !teams.data) return <div>Loading…</div>;
  const userId = league.data.user_team_id;
  if (userId == null) return <div>Pick a team to begin.</div>;
  const userGames = schedule.data.games.filter((g) => g.home_team_id === userId || g.away_team_id === userId);
  const next = userGames.find((g) => g.status === "scheduled");
  const last = [...userGames].reverse().find((g) => g.status === "simulated");
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card title="Next game">
        {next ? (
          <div>
            vs <TeamBadge teamId={next.home_team_id === userId ? next.away_team_id : next.home_team_id} /> (
            {next.home_team_id === userId ? "home" : "away"}) — matchday {next.matchday}
          </div>
        ) : (
          <div className="text-slate-500">No scheduled games.</div>
        )}
      </Card>
      <Card title="Last result">
        {last ? (
          <Link to="/game/$gameId" params={{ gameId: String(last.id) }} className="hover:underline">
            <TeamBadge teamId={last.home_team_id} /> {last.home_score} – {last.away_score}{" "}
            <TeamBadge teamId={last.away_team_id} /> <ResultBadge type={last.result_type} />
          </Link>
        ) : (
          <div className="text-slate-500">No results yet.</div>
        )}
      </Card>
      <Card title="Standings (top 4)" className="md:col-span-2">
        <Table>
          <thead>
            <tr>
              <Th>Team</Th><Th>GP</Th><Th>W</Th><Th>L</Th><Th>OTL</Th><Th>PTS</Th>
            </tr>
          </thead>
          <tbody>
            {standings.data.rows.slice(0, 4).map((r) => (
              <tr key={r.team_id} className={r.team_id === userId ? "bg-blue-50" : ""}>
                <Td><TeamBadge teamId={r.team_id} /></Td>
                <Td>{r.games_played}</Td><Td>{r.wins}</Td><Td>{r.losses}</Td>
                <Td>{r.ot_losses}</Td><Td>{r.points}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
};

export const Route = createFileRoute("/")({ component: Dashboard });
