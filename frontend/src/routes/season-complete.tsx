import { createFileRoute } from "@tanstack/react-router";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Table, Td, Th } from "../components/Table";
import { TeamBadge } from "../components/TeamBadge";
import { useCreateLeague } from "../queries/league";
import { useStandings } from "../queries/standings";

const Done = () => {
  const s = useStandings();
  const create = useCreateLeague();
  if (!s.data) return <div>Loading…</div>;
  const champ = s.data.rows[0];
  return (
    <div className="space-y-4">
      <Card title="Champion">
        <div className="text-2xl font-bold">
          <TeamBadge teamId={champ.team_id} /> wins the season — {champ.points} PTS
        </div>
      </Card>
      <Card title="Final standings">
        <Table>
          <thead>
            <tr>
              <Th>Team</Th><Th>PTS</Th><Th>W</Th><Th>L</Th><Th>OTL</Th><Th>GF</Th><Th>GA</Th>
            </tr>
          </thead>
          <tbody>
            {s.data.rows.map((r) => (
              <tr key={r.team_id}>
                <Td><TeamBadge teamId={r.team_id} /></Td>
                <Td>{r.points}</Td>
                <Td>{r.wins}</Td>
                <Td>{r.losses}</Td>
                <Td>{r.ot_losses}</Td>
                <Td>{r.goals_for}</Td>
                <Td>{r.goals_against}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <Button onClick={() => create.mutate(undefined)} disabled={create.isPending}>
        {create.isPending ? "Resetting…" : "New league"}
      </Button>
    </div>
  );
};

export const Route = createFileRoute("/season-complete")({ component: Done });
