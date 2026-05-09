import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { useGame, useSimulateGame } from "../queries/games";
import { useStandings } from "../queries/standings";
import { useTeams } from "../queries/teams";
import type { GameDetail } from "../api/types";

const Preview = () => {
  const { gameId } = Route.useParams();
  const id = Number(gameId);
  const game = useGame(id);
  const teams = useTeams();
  const standings = useStandings();
  const sim = useSimulateGame(id);
  const nav = useNavigate();

  // 0 = nothing revealed, 1-3 = periods revealed, 4 = OT revealed.
  const [revealed, setRevealed] = useState(0);

  // If the user lands on a game that's already simulated, jump to full box.
  useEffect(() => {
    if (game.data?.status === "simulated" && revealed === 0 && !sim.isPending) {
      // Don't auto-redirect — just reveal everything so the user can scrub.
      const ot = game.data.result_type === "OT" || game.data.result_type === "SO";
      setRevealed(ot ? 4 : 3);
    }
  }, [game.data?.status, game.data?.result_type, revealed, sim.isPending]);

  if (!game.data || !teams.data || !standings.data) {
    return <Shell crumbs={["Continental Hockey League", "Game Preview"]}>Loading…</Shell>;
  }
  const d = game.data;
  const home = teams.data.find((t) => t.id === d.home_team_id);
  const away = teams.data.find((t) => t.id === d.away_team_id);
  if (!home || !away) return <Shell>Missing teams</Shell>;
  const homeRow = standings.data.rows.find((r) => r.team_id === d.home_team_id);
  const awayRow = standings.data.rows.find((r) => r.team_id === d.away_team_id);

  const isSimmed = d.status === "simulated";
  const hasOT = d.result_type === "OT" || d.result_type === "SO";
  const totalPeriods = hasOT ? 4 : 3;
  const periodLabels = ["P1", "P2", "P3", "OT"];

  const ensureSim = async (): Promise<GameDetail | null> => {
    if (isSimmed) return d;
    if (sim.isPending) return null;
    try {
      return await sim.mutateAsync();
    } catch {
      return null;
    }
  };

  const revealPeriod = async (n: number) => {
    const result = await ensureSim();
    if (!result) return;
    setRevealed(Math.max(revealed, n));
  };

  const revealAll = async () => {
    const result = await ensureSim();
    if (!result) return;
    const ot = result.result_type === "OT" || result.result_type === "SO";
    setRevealed(ot ? 4 : 3);
  };

  // Cumulative score up to and including the revealed period.
  const homeShown = d.home_goals_by_period.slice(0, revealed).reduce((a, b) => a + b, 0);
  const awayShown = d.away_goals_by_period.slice(0, revealed).reduce((a, b) => a + b, 0);
  const homeShotsShown = d.home_shots_by_period.slice(0, revealed).reduce((a, b) => a + b, 0);
  const awayShotsShown = d.away_shots_by_period.slice(0, revealed).reduce((a, b) => a + b, 0);

  const fullyRevealed = isSimmed && revealed >= totalPeriods;

  return (
    <Shell
      crumbs={[
        "Continental Hockey League",
        "Schedule",
        `${away.abbreviation} @ ${home.abbreviation}`,
      ]}
    >
      <div className="section-h">
        <h1>Game Preview</h1>
        <span className="sub">Matchday {d.matchday}</span>
        <div style={{ flex: 1 }} />
        {fullyRevealed && (
          <Link to="/game/$gameId" params={{ gameId: String(d.id) }} className="btn btn-primary">
            Full Box Score →
          </Link>
        )}
      </div>

      <div
        style={{
          background: "var(--navy-900)",
          color: "#fff",
          borderRadius: 8,
          padding: "22px 28px",
          marginBottom: 14,
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr",
          alignItems: "center",
          gap: 24,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14, justifyContent: "flex-end" }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 18, fontWeight: 800 }}>{away.name}</div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>
              {away.abbreviation}
              {awayRow ? ` · ${awayRow.wins}-${awayRow.losses}-${awayRow.ot_losses}` : ""}
            </div>
          </div>
          <Logo teamId={away.id} size={56} />
        </div>
        <div style={{ textAlign: "center", minWidth: 140 }}>
          <div style={{ fontSize: 36, fontWeight: 900, fontFamily: "'Roboto Condensed', monospace" }}>
            {revealed === 0 ? "— : —" : `${awayShown} : ${homeShown}`}
          </div>
          <div style={{ fontSize: 11, opacity: 0.7, letterSpacing: "0.08em" }}>
            {revealed === 0
              ? "NOT STARTED"
              : revealed >= totalPeriods && isSimmed
                ? `FINAL${d.result_type && d.result_type !== "REG" ? ` / ${d.result_type}` : ""}`
                : `END OF ${periodLabels[revealed - 1]}`}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Logo teamId={home.id} size={56} />
          <div>
            <div style={{ fontSize: 18, fontWeight: 800 }}>{home.name}</div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>
              {home.abbreviation}
              {homeRow ? ` · ${homeRow.wins}-${homeRow.losses}-${homeRow.ot_losses}` : ""}
            </div>
          </div>
        </div>
      </div>

      <Card title="Period-by-Period">
        <div style={{ padding: "14px 18px" }}>
          <Table>
            <thead>
              <tr>
                <Th>Team</Th>
                {Array.from({ length: totalPeriods }).map((_, i) => (
                  <Th key={i} className="num">
                    {periodLabels[i]}
                  </Th>
                ))}
                <Th className="num">Total</Th>
                <Th className="num">SOG</Th>
              </tr>
            </thead>
            <tbody>
              {[
                { team: away, goals: d.away_goals_by_period, shots: d.away_shots_by_period },
                { team: home, goals: d.home_goals_by_period, shots: d.home_shots_by_period },
              ].map((row) => {
                const total = row.goals.slice(0, revealed).reduce((a, b) => a + b, 0);
                const sog = row.shots.slice(0, revealed).reduce((a, b) => a + b, 0);
                return (
                  <tr key={row.team.id}>
                    <Td>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                        <Logo teamId={row.team.id} size={20} />
                        <b>{row.team.abbreviation}</b>
                      </span>
                    </Td>
                    {Array.from({ length: totalPeriods }).map((_, i) => (
                      <Td key={i} className="num">
                        {i < revealed ? row.goals[i] ?? 0 : "—"}
                      </Td>
                    ))}
                    <Td className="num">
                      <b>{revealed === 0 ? "—" : total}</b>
                    </Td>
                    <Td className="num">{revealed === 0 ? "—" : sog}</Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </div>
      </Card>

      <Card title="Sim Controls" sub={isSimmed ? "Game complete" : "Reveal one period at a time, or run the full game."}>
        <div
          style={{
            padding: "14px 18px",
            display: "flex",
            gap: 10,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          {Array.from({ length: 3 }).map((_, i) => {
            const n = i + 1;
            const done = revealed >= n;
            const next = revealed + 1 === n;
            return (
              <button
                key={n}
                className="btn"
                disabled={sim.isPending || done || (!next && !isSimmed) || (isSimmed && done)}
                onClick={() => revealPeriod(n)}
              >
                {done ? `${periodLabels[i]} ✓` : `Sim Period ${n}`}
              </button>
            );
          })}
          {(hasOT || (revealed >= 3 && !isSimmed)) && (
            <button
              className="btn"
              disabled={sim.isPending || revealed >= 4 || revealed < 3}
              onClick={() => revealPeriod(4)}
            >
              {revealed >= 4 ? "OT ✓" : "Sim OT"}
            </button>
          )}
          <div style={{ flex: 1 }} />
          <button
            className="btn btn-primary"
            disabled={sim.isPending || fullyRevealed}
            onClick={revealAll}
          >
            {sim.isPending
              ? "Simulating…"
              : fullyRevealed
                ? "Game Complete"
                : "Sim to End of Game"}
          </button>
          {sim.error ? (
            <div style={{ width: "100%", color: "var(--red, #b91c1c)", fontSize: 12 }}>
              Failed to simulate: {String(sim.error)}
            </div>
          ) : null}
        </div>
      </Card>

      {revealed > 0 && d.events.length > 0 && (
        <Card
          title="Goals"
          sub={`Through ${revealed >= totalPeriods ? "final" : periodLabels[revealed - 1]}`}
        >
          <div style={{ padding: "8px 18px 14px" }}>
            <GoalList game={d} revealedThrough={revealed} home={home} away={away} />
          </div>
        </Card>
      )}

      <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
        <button className="btn" onClick={() => nav({ to: "/" })}>
          ← Back to Dashboard
        </button>
      </div>
    </Shell>
  );
};

const GoalList = ({
  game,
  revealedThrough,
  home,
  away,
}: {
  game: GameDetail;
  revealedThrough: number;
  home: { id: number; abbreviation: string };
  away: { id: number; abbreviation: string };
}) => {
  const goals = game.events.filter((e) => e.kind === "goal" && e.period <= revealedThrough);
  if (goals.length === 0) {
    return <div style={{ color: "var(--ink-3)", fontSize: 13 }}>No goals yet.</div>;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {goals.map((e, i) => {
        const team = e.team_id === home.id ? home : away;
        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: 13,
              padding: "4px 0",
              borderBottom: i < goals.length - 1 ? "1px solid var(--line)" : "none",
            }}
          >
            <span
              style={{
                fontFamily: "'Roboto Condensed', monospace",
                color: "var(--ink-3)",
                width: 32,
              }}
            >
              P{e.period}
            </span>
            <Logo teamId={e.team_id} size={18} />
            <b>{team.abbreviation}</b>
            <span style={{ color: "var(--ink-2)" }}>
              {e.primary_skater_name ?? "Unknown"}
              {e.assist1_name ? ` (${e.assist1_name}${e.assist2_name ? `, ${e.assist2_name}` : ""})` : ""}
            </span>
            {e.strength && e.strength !== "EV" ? (
              <span className="tag" style={{ background: "var(--bone)", color: "var(--ink-3)" }}>
                {e.strength}
              </span>
            ) : null}
          </div>
        );
      })}
    </div>
  );
};

export const Route = createFileRoute("/game-preview/$gameId")({ component: Preview });
