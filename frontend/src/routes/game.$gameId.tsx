import { createFileRoute } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { ResultBadge } from "../components/ResultBadge";
import { Table, Td, Th } from "../components/Table";
import { TeamBadge } from "../components/TeamBadge";
import { useGame } from "../queries/games";

const Box = () => {
  const { gameId } = Route.useParams();
  const g = useGame(Number(gameId));
  if (!g.data) return <div>Loading…</div>;
  return (
    <div className="space-y-4">
      <Card>
        <div className="text-2xl font-bold flex gap-3 items-center">
          <TeamBadge teamId={g.data.home_team_id} /> {g.data.home_score} – {g.data.away_score}{" "}
          <TeamBadge teamId={g.data.away_team_id} /> <ResultBadge type={g.data.result_type} />
        </div>
        <div className="text-sm text-slate-500">Shots: {g.data.home_shots} – {g.data.away_shots}</div>
      </Card>
      <Card title="Skater stats">
        <Table>
          <thead>
            <tr><Th>Skater</Th><Th>G</Th><Th>A</Th><Th>PTS</Th><Th>SOG</Th></tr>
          </thead>
          <tbody>
            {g.data.skater_stats.map((s) => (
              <tr key={s.skater_id}>
                <Td>#{s.skater_id}</Td>
                <Td>{s.goals}</Td>
                <Td>{s.assists}</Td>
                <Td>{s.goals + s.assists}</Td>
                <Td>{s.shots}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <Card title="Goalie stats">
        <Table>
          <thead>
            <tr><Th>Goalie</Th><Th>SA</Th><Th>SV</Th><Th>GA</Th><Th>SV%</Th></tr>
          </thead>
          <tbody>
            {g.data.goalie_stats.map((s) => (
              <tr key={s.goalie_id}>
                <Td>#{s.goalie_id}</Td>
                <Td>{s.shots_against}</Td>
                <Td>{s.saves}</Td>
                <Td>{s.goals_against}</Td>
                <Td>{s.shots_against ? (s.saves / s.shots_against).toFixed(3) : "—"}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <Card title="Events">
        <Table>
          <thead>
            <tr><Th>Tick</Th><Th>Kind</Th><Th>Team</Th><Th>Player</Th><Th>Goalie</Th></tr>
          </thead>
          <tbody>
            {g.data.events.map((e, i) => (
              <tr key={i}>
                <Td>{e.tick}</Td>
                <Td>{e.kind}</Td>
                <Td><TeamBadge teamId={e.team_id} /></Td>
                <Td>{e.primary_skater_id ?? "—"}</Td>
                <Td>{e.goalie_id ?? "—"}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
};

export const Route = createFileRoute("/game/$gameId")({ component: Box });
