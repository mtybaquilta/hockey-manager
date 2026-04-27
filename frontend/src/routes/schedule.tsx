import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { ResultBadge } from "../components/ResultBadge";
import { Table, Td, Th } from "../components/Table";
import { TeamBadge } from "../components/TeamBadge";
import { useLeague } from "../queries/league";
import { useSchedule } from "../queries/schedule";
import type { GameSummary } from "../api/types";

const SchedulePage = () => {
  const sched = useSchedule();
  const league = useLeague();
  const nav = useNavigate();
  if (!sched.data || !league.data) return <div>Loading…</div>;
  const userId = league.data.user_team_id;
  const byDay = new Map<number, GameSummary[]>();
  sched.data.games.forEach((g) => byDay.set(g.matchday, [...(byDay.get(g.matchday) ?? []), g]));
  return (
    <div className="space-y-3">
      {[...byDay.entries()].map(([md, games]) => (
        <Card key={md} title={`Matchday ${md}`}>
          <Table>
            <thead>
              <tr>
                <Th>Home</Th><Th></Th><Th></Th><Th></Th><Th>Away</Th><Th></Th>
              </tr>
            </thead>
            <tbody>
              {games.map((g) => {
                const isUser = g.home_team_id === userId || g.away_team_id === userId;
                const onClick = g.status === "simulated"
                  ? () => nav({ to: "/game/$gameId", params: { gameId: String(g.id) } })
                  : undefined;
                return (
                  <tr
                    key={g.id}
                    className={`${isUser ? "bg-blue-50" : ""} ${onClick ? "cursor-pointer hover:bg-slate-100" : ""}`}
                    onClick={onClick}
                  >
                    <Td><TeamBadge teamId={g.home_team_id} /></Td>
                    <Td className="text-right">{g.home_score ?? ""}</Td>
                    <Td className="text-center text-slate-400">@</Td>
                    <Td>{g.away_score ?? ""}</Td>
                    <Td><TeamBadge teamId={g.away_team_id} /></Td>
                    <Td><ResultBadge type={g.result_type} /></Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </Card>
      ))}
    </div>
  );
};

export const Route = createFileRoute("/schedule")({ component: SchedulePage });
