import { createFileRoute, Link } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Shell } from "../components/Shell";
import { usePlayoffs } from "../queries/playoffs";
import { useTeams } from "../queries/teams";
import type { PlayoffSeries } from "../api/types";

const ROUND_LABELS: Record<number, string> = {
  1: "First Round",
  2: "Quarterfinals",
  3: "Semifinals",
  4: "Final",
};

const SeriesCard = ({ s }: { s: PlayoffSeries }) => {
  const teams = useTeams();
  const high = teams.data?.find((t) => t.id === s.high_seed_team_id);
  const low = teams.data?.find((t) => t.id === s.low_seed_team_id);
  const highWon = s.winner_team_id === s.high_seed_team_id;
  const lowWon = s.winner_team_id === s.low_seed_team_id;
  const lastGame = s.games.length ? s.games[s.games.length - 1] : null;
  return (
    <div
      style={{
        border: "1px solid var(--line)",
        borderRadius: 6,
        background: "#fff",
        padding: 10,
        minWidth: 220,
        opacity: s.status === "complete" ? 0.95 : 1,
      }}
    >
      <Row
        seed={s.high_seed}
        teamId={s.high_seed_team_id}
        teamName={high?.name}
        wins={s.wins_high}
        won={highWon}
        eliminated={s.status === "complete" && lowWon}
      />
      <div style={{ height: 1, background: "var(--line)", margin: "6px 0" }} />
      <Row
        seed={s.low_seed}
        teamId={s.low_seed_team_id}
        teamName={low?.name}
        wins={s.wins_low}
        won={lowWon}
        eliminated={s.status === "complete" && highWon}
      />
      <div
        style={{
          marginTop: 8,
          fontSize: 10,
          color: "var(--ink-3)",
          fontFamily: "'Roboto Condensed', monospace",
          letterSpacing: "0.04em",
        }}
      >
        {s.status === "complete"
          ? `Series ${s.wins_high}-${s.wins_low}`
          : lastGame
          ? `Game ${lastGame.game_in_series} · MD ${lastGame.matchday}`
          : "Series upcoming"}
      </div>
    </div>
  );
};

const Row = ({
  seed,
  teamId,
  teamName,
  wins,
  won,
  eliminated,
}: {
  seed: number;
  teamId: number | null;
  teamName: string | undefined;
  wins: number;
  won: boolean;
  eliminated: boolean;
}) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 8,
      opacity: eliminated ? 0.45 : 1,
      fontWeight: won ? 700 : 500,
    }}
  >
    <span
      style={{
        width: 22,
        textAlign: "center",
        fontFamily: "'Roboto Condensed', monospace",
        fontSize: 11,
        color: "var(--ink-3)",
      }}
    >
      {seed}
    </span>
    {teamId != null ? <Logo teamId={teamId} size={22} /> : <span style={{ width: 22 }} />}
    <span style={{ flex: 1, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
      {teamName ?? "—"}
    </span>
    <span
      style={{
        fontFamily: "'Roboto Condensed', monospace",
        fontSize: 16,
        fontWeight: 700,
        color: won ? "var(--green)" : "var(--ink-2)",
      }}
    >
      {wins}
    </span>
  </div>
);

const PlayoffsPage = () => {
  const pf = usePlayoffs();
  const teams = useTeams();
  if (!pf.data || !teams.data) {
    return <Shell crumbs={["Continental Hockey League", "Playoffs"]}>Loading…</Shell>;
  }

  if (pf.data.phase === "regular_season") {
    return (
      <Shell crumbs={["Continental Hockey League", "Playoffs"]}>
        <Card title="Playoffs">
          <div style={{ padding: 24, color: "var(--ink-3)" }}>
            Playoffs begin after the regular season. Top 16 teams qualify.{" "}
            <Link to="/standings" className="link">
              View standings →
            </Link>
          </div>
        </Card>
      </Shell>
    );
  }

  const champ =
    pf.data.champion_team_id != null
      ? teams.data.find((t) => t.id === pf.data!.champion_team_id)
      : undefined;

  return (
    <Shell crumbs={["Continental Hockey League", "Playoffs"]}>
      <div className="section-h">
        <h1>Playoffs</h1>
        <span className="sub">Top-16 bracket · Best-of-7</span>
      </div>

      {champ && (
        <div
          style={{
            background: "linear-gradient(110deg, var(--navy-800) 0%, var(--navy-700) 60%, var(--navy-600) 100%)",
            color: "#fff",
            borderRadius: 8,
            padding: "20px 24px",
            marginBottom: 18,
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <Logo teamId={champ.id} size={56} />
          <div>
            <div style={{ fontSize: 11, letterSpacing: "0.18em", color: "rgba(255,255,255,.6)", textTransform: "uppercase", fontWeight: 700 }}>
              Cup Champion
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em" }}>
              {champ.name}
            </div>
          </div>
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 14,
          alignItems: "start",
        }}
      >
        {[1, 2, 3, 4].map((r) => {
          const round = pf.data!.rounds.find((x) => x.round === r);
          return (
            <div key={r}>
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: "0.12em",
                  color: "var(--ink-3)",
                  textTransform: "uppercase",
                  fontWeight: 700,
                  marginBottom: 8,
                  padding: "0 4px",
                }}
              >
                {ROUND_LABELS[r]}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {round
                  ? round.series.map((s) => <SeriesCard key={s.id} s={s} />)
                  : (
                    <div
                      style={{
                        border: "1px dashed var(--line)",
                        borderRadius: 6,
                        padding: 14,
                        color: "var(--ink-4)",
                        fontSize: 12,
                      }}
                    >
                      —
                    </div>
                  )}
              </div>
            </div>
          );
        })}
      </div>
    </Shell>
  );
};

export const Route = createFileRoute("/playoffs")({ component: PlayoffsPage });
