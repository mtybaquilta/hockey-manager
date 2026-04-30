import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Card } from "../components/Card";
import { Logo, TeamRow } from "../components/Logo";
import { ResultBadge } from "../components/ResultBadge";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { useLeague } from "../queries/league";
import { useSchedule } from "../queries/schedule";
import { useAdvance, useSeasonStatus, useSimTo } from "../queries/season";
import { useStandings } from "../queries/standings";
import { useTeams } from "../queries/teams";

const Dashboard = () => {
  const league = useLeague();
  const schedule = useSchedule();
  const standings = useStandings();
  const teams = useTeams();
  const status = useSeasonStatus();
  const advance = useAdvance();
  const simTo = useSimTo();
  const [simTarget, setSimTarget] = useState<string>("");
  const nav = useNavigate();

  if (!league.data || !schedule.data || !standings.data || !teams.data) {
    return <Shell crumbs={["Continental Hockey League", "Dashboard"]}>Loading…</Shell>;
  }
  const userId = league.data.user_team_id;
  if (userId == null) {
    return (
      <Shell crumbs={["Continental Hockey League", "Dashboard"]}>
        <div style={{ color: "var(--ink-3)" }}>Pick a team to begin.</div>
      </Shell>
    );
  }
  const me = teams.data.find((t) => t.id === userId)!;
  const myRow = standings.data.rows.find((r) => r.team_id === userId);
  const myRank = standings.data.rows.findIndex((r) => r.team_id === userId) + 1;
  const userGames = schedule.data.games.filter((g) => g.home_team_id === userId || g.away_team_id === userId);
  const next = userGames.find((g) => g.status === "scheduled");
  const recent = userGames.filter((g) => g.status === "simulated").slice(-6).reverse();
  const opp = next ? (next.home_team_id === userId ? next.away_team_id : next.home_team_id) : null;
  const oppT = opp != null ? teams.data.find((t) => t.id === opp) : undefined;
  const oppRow = opp != null ? standings.data.rows.find((r) => r.team_id === opp) : undefined;
  const isAway = next ? next.away_team_id === userId : false;
  const top5 = standings.data.rows.slice(0, 5);
  const diff = myRow ? myRow.goals_for - myRow.goals_against : 0;
  const seasonComplete = status.data?.status === "complete";

  const onAdvance = () =>
    advance.mutate(undefined, {
      onSuccess: (r) => {
        if (r.season_status === "complete") nav({ to: "/season-complete" });
      },
    });

  const ord = (n: number) => (n === 1 ? "st" : n === 2 ? "nd" : n === 3 ? "rd" : "th");

  return (
    <Shell crumbs={["Continental Hockey League", "Dashboard"]}>
      <div className="section-h">
        <h1>Dashboard</h1>
        <span className="sub">{me.name} · '25-26 Regular Season</span>
        <div style={{ flex: 1 }} />
        {seasonComplete ? (
          <Link to="/season-complete" className="btn btn-primary">
            Season complete →
          </Link>
        ) : (
          <button className="btn btn-primary" disabled={advance.isPending} onClick={onAdvance}>
            {advance.isPending ? "Simulating…" : "Sim to Next Matchday →"}
          </button>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr 1fr", gap: 14, marginBottom: 18 }}>
        <div className="next-card">
          <div className="label">Next Game · Matchday {next?.matchday ?? "—"}</div>
          {next && oppT ? (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 10 }}>
                <Logo teamId={oppT.id} size={44} />
                <div>
                  <div className="opp">
                    {isAway ? "@ " : "vs "}
                    {oppT.name}
                  </div>
                  <div className="when">
                    {oppT.abbreviation}
                    {oppRow ? ` · ${oppRow.wins}-${oppRow.losses}-${oppRow.ot_losses}` : ""}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div style={{ marginTop: 10, color: "rgba(255,255,255,.7)" }}>No upcoming games.</div>
          )}
        </div>
        <div className="k-stat">
          <div className="lbl">Record</div>
          <div className="val">
            {myRow ? `${myRow.wins}-${myRow.losses}-${myRow.ot_losses}` : "—"}
          </div>
          <div className={`delta ${diff < 0 ? "bad" : ""}`}>
            {diff > 0 ? "+" : ""}
            {diff} differential
          </div>
        </div>
        <div className="k-stat">
          <div className="lbl">League Rank</div>
          <div className="val">
            {myRank || "—"}
            {myRank ? <span style={{ fontSize: 14, color: "var(--ink-3)" }}>{ord(myRank)}</span> : null}
          </div>
          <div className="delta">{myRow?.points ?? 0} PTS</div>
        </div>
        <div className="k-stat">
          <div className="lbl">Games Played</div>
          <div className="val">{myRow?.games_played ?? 0}</div>
          <div className="delta">{recent.length} recent results</div>
        </div>
      </div>

      {!seasonComplete && (
        <Card title="Dev · Sim Forward" sub="dev only">
          <div style={{ padding: "12px 16px", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: "var(--ink-3)" }}>Sim to matchday</span>
            <input
              type="number"
              min={status.data?.current_matchday ?? 1}
              value={simTarget}
              placeholder={String(status.data?.current_matchday ?? 1)}
              onChange={(e) => setSimTarget(e.target.value)}
              style={{ width: 80, padding: "4px 8px", border: "1px solid var(--line)", borderRadius: 4, fontFamily: "'Roboto Condensed', monospace" }}
            />
            <button
              className="btn"
              disabled={simTo.isPending || !simTarget}
              onClick={() => {
                const n = Number(simTarget);
                if (!Number.isFinite(n) || n < 1) return;
                simTo.mutate(n, {
                  onSuccess: (r) => {
                    if (r.season_status === "complete") nav({ to: "/season-complete" });
                  },
                });
              }}
            >
              {simTo.isPending ? "Simulating…" : "Go"}
            </button>
            <div style={{ flex: 1 }} />
            <button
              className="btn btn-primary"
              disabled={simTo.isPending}
              onClick={() =>
                simTo.mutate(undefined, {
                  onSuccess: (r) => {
                    if (r.season_status === "complete") nav({ to: "/season-complete" });
                  },
                })
              }
            >
              {simTo.isPending ? "Simulating…" : "Sim to End of Season"}
            </button>
          </div>
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 14, marginTop: 14 }}>
        <Card
          title="Recent Results"
          sub="Last 6"
          link={
            <Link to="/schedule" className="link">
              Schedule →
            </Link>
          }
        >
          <Table>
            <tbody>
              {recent.length === 0 && (
                <tr>
                  <Td colSpan={6} style={{ color: "var(--ink-3)", textAlign: "center", padding: 20 }}>
                    No results yet.
                  </Td>
                </tr>
              )}
              {recent.map((g) => {
                const meIsHome = g.home_team_id === userId;
                const myScore = meIsHome ? g.home_score : g.away_score;
                const oppScore = meIsHome ? g.away_score : g.home_score;
                const won = (myScore ?? 0) > (oppScore ?? 0);
                return (
                  <tr
                    key={g.id}
                    style={{ cursor: "pointer" }}
                    onClick={() => nav({ to: "/game/$gameId", params: { gameId: String(g.id) } })}
                  >
                    <Td style={{ width: 70, color: "var(--ink-3)", fontSize: 11 }}>MD {g.matchday}</Td>
                    <Td>
                      <TeamRow teamId={g.away_team_id} />
                    </Td>
                    <Td className="num">{g.away_score}</Td>
                    <Td style={{ width: 8, color: "var(--ink-4)" }}>at</Td>
                    <Td>
                      <TeamRow teamId={g.home_team_id} />
                    </Td>
                    <Td className="num">{g.home_score}</Td>
                    <Td style={{ width: 50 }}>
                      <ResultBadge type={g.result_type} />
                    </Td>
                    <Td style={{ width: 24 }}>
                      <span className={`tag ${won ? "tag-w" : "tag-l"}`}>{won ? "W" : "L"}</span>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </Card>
        <Card
          title="Standings"
          sub="Top 5"
          link={
            <Link to="/standings" className="link">
              Full →
            </Link>
          }
        >
          <Table>
            <thead>
              <tr>
                <Th></Th>
                <Th>Team</Th>
                <Th className="num">GP</Th>
                <Th className="num">PTS</Th>
                <Th className="num">DIFF</Th>
              </tr>
            </thead>
            <tbody>
              {top5.map((r, i) => {
                const d = r.goals_for - r.goals_against;
                return (
                  <tr key={r.team_id} className={r.team_id === userId ? "me" : ""}>
                    <Td className="rank">{i + 1}</Td>
                    <Td>
                      <TeamRow teamId={r.team_id} />
                    </Td>
                    <Td className="num">{r.games_played}</Td>
                    <Td className="num">
                      <b>{r.points}</b>
                    </Td>
                    <Td
                      className="num"
                      style={{ color: d >= 0 ? "var(--green)" : "var(--red)", fontWeight: 700 }}
                    >
                      {d > 0 ? "+" : ""}
                      {d}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </Card>
      </div>
    </Shell>
  );
};

export const Route = createFileRoute("/")({ component: Dashboard });
