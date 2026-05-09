import { createFileRoute, Link } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Shell } from "../components/Shell";
import { useLeague } from "../queries/league";
import { usePlayoffs } from "../queries/playoffs";
import { useTeams } from "../queries/teams";
import type { PlayoffSeries } from "../api/types";

const ROUND_LABELS: Record<number, string> = {
  1: "Round 1",
  2: "Quarterfinals",
  3: "Semifinals",
  4: "Final",
};

const SeriesCard = ({ s, userId }: { s: PlayoffSeries; userId: number | null }) => {
  const teams = useTeams();
  const high = teams.data?.find((t) => t.id === s.high_seed_team_id);
  const low = teams.data?.find((t) => t.id === s.low_seed_team_id);
  const highWon = s.winner_team_id === s.high_seed_team_id;
  const lowWon = s.winner_team_id === s.low_seed_team_id;
  const isLive = s.status === "active" && (s.wins_high > 0 || s.wins_low > 0);
  const isFinal = s.status === "complete";
  const meIsHere =
    userId != null && (s.high_seed_team_id === userId || s.low_seed_team_id === userId);

  return (
    <div
      style={{
        background: isLive
          ? "linear-gradient(180deg, #1a2944, var(--surface))"
          : "var(--surface)",
        border: isLive ? "1px solid rgba(125,211,252,0.4)" : "1px solid var(--line-2)",
        borderRadius: 8,
        overflow: "visible",
        boxShadow: isLive
          ? "0 0 0 3px rgba(125,211,252,0.07), 0 8px 24px -8px rgba(125,211,252,0.25)"
          : "var(--shadow-1)",
        position: "relative",
      }}
    >
      {isLive && (
        <div
          style={{
            position: "absolute",
            top: -8,
            right: 8,
            background: "var(--ice)",
            color: "#031018",
            font: "900 8px/1 var(--font-mono)",
            letterSpacing: "0.2em",
            padding: "3px 7px",
            borderRadius: 3,
            boxShadow: "0 0 8px rgba(125,211,252,0.6)",
            zIndex: 2,
          }}
        >
          ● LIVE
        </div>
      )}
      {isFinal && (
        <div
          style={{
            position: "absolute",
            top: -8,
            right: 8,
            background: "var(--bg-deep)",
            color: "var(--amber)",
            font: "800 8px/1 var(--font-mono)",
            letterSpacing: "0.2em",
            padding: "3px 7px",
            borderRadius: 3,
            border: "1px solid rgba(251,191,36,0.4)",
            zIndex: 2,
          }}
        >
          FINAL
        </div>
      )}
      <Row
        seed={s.high_seed}
        teamId={s.high_seed_team_id}
        teamName={high?.name}
        wins={s.wins_high}
        won={highWon}
        eliminated={isFinal && lowWon}
        isMe={meIsHere && s.high_seed_team_id === userId}
        showScore={s.wins_high > 0 || s.wins_low > 0 || isFinal}
      />
      <div style={{ height: 1, background: "var(--line)" }} />
      <Row
        seed={s.low_seed}
        teamId={s.low_seed_team_id}
        teamName={low?.name}
        wins={s.wins_low}
        won={lowWon}
        eliminated={isFinal && highWon}
        isMe={meIsHere && s.low_seed_team_id === userId}
        showScore={s.wins_high > 0 || s.wins_low > 0 || isFinal}
      />
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
  isMe,
  showScore,
}: {
  seed: number;
  teamId: number | null;
  teamName: string | undefined;
  wins: number;
  won: boolean;
  eliminated: boolean;
  isMe: boolean;
  showScore: boolean;
}) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "9px 10px",
      background: won ? "rgba(125,211,252,0.08)" : "transparent",
      opacity: eliminated ? 0.45 : 1,
      position: "relative",
    }}
  >
    {isMe && (
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 2,
          bottom: 2,
          width: 2,
          background: "var(--amber)",
        }}
      />
    )}
    <span
      style={{
        width: 18,
        textAlign: "center",
        fontFamily: "var(--font-num)",
        fontSize: 13,
        fontWeight: 800,
        color: won ? "var(--ink)" : "var(--ink-3)",
      }}
    >
      {seed || "—"}
    </span>
    {teamId != null ? <Logo teamId={teamId} size={22} /> : <span style={{ width: 22, height: 22 }} />}
    <span
      style={{
        flex: 1,
        fontSize: 12,
        fontWeight: won ? 800 : 600,
        color: won ? "var(--ink)" : "var(--ink-2)",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
    >
      {teamName ?? "TBD"}
    </span>
    {showScore && (
      <span
        style={{
          font: "800 16px/1 var(--font-num)",
          color: won ? "var(--ice)" : "var(--ink-3)",
          minWidth: 18,
          textAlign: "right",
        }}
      >
        {wins}
      </span>
    )}
  </div>
);

const PlayoffsPage = () => {
  const pf = usePlayoffs();
  const teams = useTeams();
  const league = useLeague();
  const userId = league.data?.user_team_id ?? null;

  if (!pf.data || !teams.data) {
    return <Shell crumbs={["Continental Hockey League", "Playoffs"]}>Loading…</Shell>;
  }

  if (pf.data.phase === "regular_season") {
    return (
      <Shell crumbs={["Continental Hockey League", "Playoffs"]}>
        <Card title="Playoffs">
          <div style={{ padding: 28, color: "var(--ink-2)", lineHeight: 1.6 }}>
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

  const myActiveSeries = pf.data.rounds
    .flatMap((r) => r.series)
    .find((s) => userId != null && s.status === "active" && (s.high_seed_team_id === userId || s.low_seed_team_id === userId));

  const myWins = myActiveSeries
    ? myActiveSeries.high_seed_team_id === userId
      ? myActiveSeries.wins_high
      : myActiveSeries.wins_low
    : 0;
  const oppWins = myActiveSeries
    ? myActiveSeries.high_seed_team_id === userId
      ? myActiveSeries.wins_low
      : myActiveSeries.wins_high
    : 0;
  const oppId = myActiveSeries
    ? myActiveSeries.high_seed_team_id === userId
      ? myActiveSeries.low_seed_team_id
      : myActiveSeries.high_seed_team_id
    : null;
  const oppT = oppId != null ? teams.data.find((t) => t.id === oppId) : undefined;

  return (
    <Shell crumbs={["Continental Hockey League", "Playoffs"]}>
      {/* Title strip — broadcast hero */}
      <div
        style={{
          background:
            "linear-gradient(115deg, #1a3650 0%, #0e1e3a 50%, #2a1d3d 100%)",
          borderRadius: 14,
          padding: "16px 24px",
          border: "1px solid var(--line-2)",
          position: "relative",
          overflow: "hidden",
          marginBottom: 16,
          boxShadow: "var(--shadow-2)",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: -60,
            right: -40,
            width: 260,
            height: 260,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(251,191,36,0.22), transparent 60%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 18,
            position: "relative",
          }}
        >
          <div>
            <div className="kicker amber">★ The Chase for the Continental Cup</div>
            <div
              style={{
                font: "900 30px/1 var(--font-display)",
                letterSpacing: "-0.02em",
                marginTop: 6,
                color: "var(--ink)",
              }}
            >
              Stanley Bracket · 16 Teams
            </div>
          </div>
          <div style={{ display: "flex", gap: 18, alignItems: "center" }}>
            {champ ? (
              <div style={{ textAlign: "right" }}>
                <div className="kicker amber">CUP CHAMPION</div>
                <div
                  style={{
                    font: "900 22px/1 var(--font-display)",
                    color: "var(--amber)",
                    marginTop: 4,
                    letterSpacing: "-0.01em",
                  }}
                >
                  {champ.name}
                </div>
              </div>
            ) : myActiveSeries && oppT ? (
              <>
                <div style={{ textAlign: "right" }}>
                  <div className="kicker">YOUR SERIES</div>
                  <div
                    style={{
                      font: "800 22px/1 var(--font-num)",
                      color: "var(--amber)",
                      marginTop: 4,
                      letterSpacing: "0.02em",
                    }}
                  >
                    {myWins} — {oppWins} vs {oppT.abbreviation}
                  </div>
                  <div
                    style={{
                      font: "600 10px/1 var(--font-mono)",
                      color: "var(--ice)",
                      marginTop: 4,
                      letterSpacing: "0.15em",
                      textTransform: "uppercase",
                    }}
                  >
                    Best-of-7 · Win 4 to advance
                  </div>
                </div>
              </>
            ) : null}
          </div>
        </div>
      </div>

      {/* Bracket */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--line-2)",
          borderRadius: 14,
          padding: "22px 22px 24px",
          overflow: "auto",
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr auto",
            gap: 18,
            alignItems: "start",
            minWidth: 1000,
          }}
        >
          {[1, 2, 3].map((r) => {
            const round = pf.data!.rounds.find((x) => x.round === r);
            const seriesCount = round?.series.length ?? 0;
            return (
              <div key={r}>
                <div
                  style={{
                    font: "700 10px/1 var(--font-mono)",
                    letterSpacing: "0.25em",
                    color: "var(--ink-3)",
                    textTransform: "uppercase",
                    paddingBottom: 8,
                    borderBottom: "1px solid var(--line)",
                    marginBottom: 14,
                  }}
                >
                  {ROUND_LABELS[r]}{seriesCount ? ` · ${seriesCount}` : ""}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {round && round.series.length > 0
                    ? round.series.map((s) => (
                        <SeriesCard key={s.id} s={s} userId={userId} />
                      ))
                    : Array.from({ length: r === 1 ? 8 : r === 2 ? 4 : 2 }).map((_, i) => (
                        <PlaceholderSeries key={i} />
                      ))}
                </div>
              </div>
            );
          })}

          {/* Final + Cup terminus */}
          <div style={{ minWidth: 240 }}>
            <div
              style={{
                font: "700 10px/1 var(--font-mono)",
                letterSpacing: "0.25em",
                color: "var(--amber)",
                textTransform: "uppercase",
                paddingBottom: 8,
                borderBottom: "1px solid rgba(251,191,36,0.3)",
                marginBottom: 14,
              }}
            >
              ★ Final
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14, alignItems: "stretch" }}>
              {pf.data!.rounds.find((x) => x.round === 4)?.series.map((s) => (
                <SeriesCard key={s.id} s={s} userId={userId} />
              )) ?? <PlaceholderSeries />}
              <CupTerminus champion={champ} />
            </div>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div
        style={{
          marginTop: 14,
          display: "flex",
          gap: 18,
          alignItems: "center",
          font: "600 10px/1 var(--font-mono)",
          color: "var(--ink-3)",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: 8,
              background: "var(--ice)",
              boxShadow: "0 0 6px var(--ice)",
            }}
          />
          Live series
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: 2,
              background: "rgba(251,191,36,0.4)",
              border: "1px solid var(--amber)",
            }}
          />
          Final · advanced
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 8, height: 8, background: "var(--amber)" }} />
          Your franchise
        </span>
        <span style={{ flex: 1 }} />
        <span>Best-of-7 · Win 4 to advance</span>
      </div>
    </Shell>
  );
};

const PlaceholderSeries = () => (
  <div
    style={{
      border: "1px dashed var(--line-2)",
      borderRadius: 8,
      padding: 14,
      color: "var(--ink-3)",
      fontSize: 11,
      fontFamily: "var(--font-mono)",
      letterSpacing: "0.15em",
      textTransform: "uppercase",
      textAlign: "center",
    }}
  >
    TBD
  </div>
);

const CupTerminus = ({ champion }: { champion?: { id: number; name: string } }) => (
  <div
    style={{
      padding: "20px 16px",
      background:
        "radial-gradient(ellipse at center, rgba(251,191,36,0.2), rgba(251,191,36,0.06) 60%, transparent 100%)",
      borderRadius: 16,
      textAlign: "center",
    }}
  >
    <div className="kicker amber">★ Champion</div>
    <div
      style={{
        font: "900 22px/1.05 var(--font-display)",
        letterSpacing: "-0.02em",
        background: "linear-gradient(180deg, var(--amber), var(--amber-deep))",
        WebkitBackgroundClip: "text",
        WebkitTextFillColor: "transparent",
        marginTop: 6,
      }}
    >
      Continental
      <br />
      Cup
    </div>
    <div
      style={{
        margin: "14px auto",
        width: 56,
        height: 56,
        borderRadius: 56,
        background:
          "radial-gradient(circle at 40% 30%, var(--amber), var(--amber-deep) 70%, #6e3a06)",
        boxShadow:
          "0 0 30px rgba(251,191,36,0.5), inset 0 4px 8px rgba(255,255,255,0.4)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        font: "900 26px/1 var(--font-display)",
        color: "#3d2410",
      }}
    >
      ★
    </div>
    <div
      style={{
        font: "600 10px/1 var(--font-mono)",
        color: champion ? "var(--amber)" : "var(--ink-3)",
        letterSpacing: "0.2em",
        textTransform: "uppercase",
      }}
    >
      {champion ? champion.name : "Champion TBD"}
    </div>
  </div>
);

export const Route = createFileRoute("/playoffs")({ component: PlayoffsPage });
