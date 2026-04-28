import { createFileRoute } from "@tanstack/react-router";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Table, Td, Th } from "../components/Table";
import { TeamBadge } from "../components/TeamBadge";
import { useCreateLeague } from "../queries/league";
import { useSeasonStats } from "../queries/season";
import { useStandings } from "../queries/standings";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const num = (v: number) => v.toFixed(2);

const Done = () => {
  const s = useStandings();
  const stats = useSeasonStats();
  const create = useCreateLeague();
  if (!s.data || !stats.data) return <div>Loading…</div>;
  const champ = s.data.rows[0];
  const st = stats.data;
  return (
    <div className="space-y-4">
      <Card title="Champion">
        <div className="text-2xl font-bold">
          <TeamBadge teamId={champ.team_id} /> wins the season — {champ.points} PTS
        </div>
      </Card>
      <Card title="Season averages">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-2 text-sm">
          <div><span className="text-slate-500">Games played:</span> {st.games_played}</div>
          <div><span className="text-slate-500">Goals/game:</span> {num(st.avg_total_goals_per_game)}</div>
          <div><span className="text-slate-500">Shots/game:</span> {num(st.avg_total_shots_per_game)}</div>
          <div><span className="text-slate-500">Home G/A goals:</span> {num(st.avg_home_goals)} / {num(st.avg_away_goals)}</div>
          <div><span className="text-slate-500">Home/Away shots:</span> {num(st.avg_home_shots)} / {num(st.avg_away_shots)}</div>
          <div><span className="text-slate-500">Home win%:</span> {pct(st.home_win_pct)}</div>
          <div><span className="text-slate-500">League SV%:</span> {pct(st.league_save_percentage)}</div>
          <div><span className="text-slate-500">League SH%:</span> {pct(st.league_shooting_percentage)}</div>
          <div><span className="text-slate-500">OT / SO:</span> {pct(st.overtime_pct)} / {pct(st.shootout_pct)}</div>
          <div><span className="text-slate-500">Penalties/game:</span> {num(st.penalties_per_game)}</div>
          <div><span className="text-slate-500">PP goals/game:</span> {num(st.pp_goals_per_game)}</div>
          <div><span className="text-slate-500">SH goals/game:</span> {num(st.sh_goals_per_game)}</div>
        </div>
      </Card>
      <Card title="Season leaders">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <div>
            <span className="text-slate-500">Top scorer:</span>{" "}
            {st.top_scorer_name ? `${st.top_scorer_name} — ${st.top_scorer_points} PTS (${st.top_scorer_goals}G ${st.top_scorer_assists}A)` : "—"}
          </div>
          <div>
            <span className="text-slate-500">Top goalie (≥30 SA):</span>{" "}
            {st.top_goalie_name ? `${st.top_goalie_name} — ${pct(st.top_goalie_save_pct)} SV% on ${st.top_goalie_shots_against} SA` : "—"}
          </div>
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
