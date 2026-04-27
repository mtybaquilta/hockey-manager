import { createFileRoute } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Table, Td, Th } from "../components/Table";
import { TeamBadge } from "../components/TeamBadge";
import { useLeague } from "../queries/league";
import { useStandings } from "../queries/standings";

const StandingsPage = () => {
  const s = useStandings();
  const l = useLeague();
  if (!s.data || !l.data) return <div>Loading…</div>;
  const userId = l.data.user_team_id;
  return (
    <Card title="Standings">
      <Table>
        <thead>
          <tr>
            <Th>Team</Th><Th>GP</Th><Th>W</Th><Th>L</Th><Th>OTL</Th>
            <Th>PTS</Th><Th>GF</Th><Th>GA</Th><Th>DIFF</Th>
          </tr>
        </thead>
        <tbody>
          {s.data.rows.map((r) => (
            <tr key={r.team_id} className={r.team_id === userId ? "bg-blue-50" : ""}>
              <Td><TeamBadge teamId={r.team_id} /></Td>
              <Td>{r.games_played}</Td>
              <Td>{r.wins}</Td>
              <Td>{r.losses}</Td>
              <Td>{r.ot_losses}</Td>
              <Td className="font-semibold">{r.points}</Td>
              <Td>{r.goals_for}</Td>
              <Td>{r.goals_against}</Td>
              <Td>{r.goals_for - r.goals_against}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
};

export const Route = createFileRoute("/standings")({ component: StandingsPage });
