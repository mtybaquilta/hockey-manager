import { createFileRoute, Link, Outlet, useMatchRoute } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Table, Td, Th } from "../components/Table";
import { useLeague } from "../queries/league";
import { useRoster } from "../queries/teams";

const TeamPage = () => {
  const { teamId } = Route.useParams();
  const id = Number(teamId);
  const roster = useRoster(id);
  const league = useLeague();
  const matchRoute = useMatchRoute();
  const isChild = matchRoute({ to: "/team/$teamId/lineup", params: { teamId } });
  if (isChild) return <Outlet />;
  if (!roster.data || !league.data) return <div>Loading…</div>;
  const isUser = league.data.user_team_id === id;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">{roster.data.team.name}</h2>
        {isUser && (
          <Link to="/team/$teamId/lineup" params={{ teamId }} className="text-blue-700 hover:underline">
            Edit lineup
          </Link>
        )}
      </div>
      <Card title="Skaters">
        <Table>
          <thead>
            <tr>
              <Th>Pos</Th><Th>Name</Th><Th>Age</Th>
              <Th>SK</Th><Th>SH</Th><Th>PA</Th><Th>DE</Th><Th>PH</Th>
            </tr>
          </thead>
          <tbody>
            {roster.data.skaters.map((s) => (
              <tr key={s.id}>
                <Td>{s.position}</Td>
                <Td>{s.name}</Td>
                <Td>{s.age}</Td>
                <Td>{s.skating}</Td>
                <Td>{s.shooting}</Td>
                <Td>{s.passing}</Td>
                <Td>{s.defense}</Td>
                <Td>{s.physical}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <Card title="Goalies">
        <Table>
          <thead>
            <tr>
              <Th>Name</Th><Th>Age</Th>
              <Th>RX</Th><Th>PO</Th><Th>RC</Th><Th>PH</Th><Th>ME</Th>
            </tr>
          </thead>
          <tbody>
            {roster.data.goalies.map((g) => (
              <tr key={g.id}>
                <Td>{g.name}</Td>
                <Td>{g.age}</Td>
                <Td>{g.reflexes}</Td>
                <Td>{g.positioning}</Td>
                <Td>{g.rebound_control}</Td>
                <Td>{g.puck_handling}</Td>
                <Td>{g.mental}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
};

export const Route = createFileRoute("/team/$teamId")({ component: TeamPage });
