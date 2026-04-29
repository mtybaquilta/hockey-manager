import { createFileRoute, Link } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Pagination, usePager } from "../components/Pagination";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { useGame } from "../queries/games";
import { useTeams } from "../queries/teams";
import { HmApiError } from "../api/client";
import type { GameDetail } from "../api/types";

const Box = () => {
  const { gameId } = Route.useParams();
  const g = useGame(Number(gameId));
  const teams = useTeams();
  if (g.error instanceof HmApiError && g.error.code === "GameNotFound") {
    return (
      <Shell crumbs={["Continental Hockey League", "Schedule", "Not found"]}>
        <Card title="Game not found">
          <div style={{ padding: "16px 18px", color: "var(--ink-3)" }}>
            Game #{gameId} doesn't exist in the current league. It may belong to a previous season.
            <div style={{ marginTop: 12 }}>
              <Link to="/schedule" className="btn btn-primary">
                Back to schedule
              </Link>
            </div>
          </div>
        </Card>
      </Shell>
    );
  }
  if (!g.data || !teams.data) return <Shell crumbs={["Continental Hockey League", "Game"]}>Loading…</Shell>;
  const d = g.data;
  const home = teams.data.find((t) => t.id === d.home_team_id);
  const away = teams.data.find((t) => t.id === d.away_team_id);
  if (!home || !away) return <Shell>Missing teams</Shell>;

  const homeGoalsByPeriod = d.home_goals_by_period;
  const awayGoalsByPeriod = d.away_goals_by_period;
  const hasOT = d.result_type === "OT" || d.result_type === "SO";
  const periodLabels = hasOT ? ["P1", "P2", "P3", "OT"] : ["P1", "P2", "P3"];
  const skaterPager = usePager(d.skater_stats);
  const goaliePager = usePager(d.goalie_stats);
  const eventPager = usePager(d.events);

  return (
    <Shell crumbs={["Continental Hockey League", "Schedule", `${away.abbreviation} vs ${home.abbreviation}`]}>
      {/* Scoreboard ribbon */}
      <div
        style={{
          background: "var(--navy-900)",
          color: "#fff",
          borderRadius: 8,
          overflow: "hidden",
          marginBottom: 14,
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            right: -60,
            top: -40,
            width: 240,
            height: 240,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(220,38,38,.16) 0%, transparent 70%)",
          }}
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr auto 1fr",
            alignItems: "center",
            padding: "18px 28px",
            gap: 24,
            position: "relative",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14, justifyContent: "flex-end" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,.55)", letterSpacing: "0.14em", fontWeight: 700 }}>
                AWAY
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, marginTop: 2 }}>{away.name}</div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,.5)" }}>
                SHOTS {d.away_shots ?? 0}
              </div>
            </div>
            <Logo teamId={away.id} size={56} />
            <div style={{ font: "700 56px/1 'Roboto Condensed', monospace", minWidth: 60, textAlign: "center" }}>
              {d.away_score ?? "—"}
            </div>
          </div>
          <div
            style={{
              textAlign: "center",
              padding: "0 12px",
              borderLeft: "1px solid rgba(255,255,255,.12)",
              borderRight: "1px solid rgba(255,255,255,.12)",
            }}
          >
            <span className="tag tag-final" style={{ fontSize: 10, background: "var(--gold)", color: "#fff" }}>
              {d.status === "simulated" ? "FINAL" : "SCHEDULED"}
            </span>
            <div style={{ font: "700 22px/1 'Roboto Condensed', monospace", marginTop: 8, color: "var(--gold)" }}>
              MD {d.matchday}
            </div>
            {d.result_type && d.result_type !== "REG" && (
              <div style={{ fontSize: 10, color: "rgba(255,255,255,.55)", letterSpacing: "0.14em", fontWeight: 700, marginTop: 6 }}>
                ENDED IN {d.result_type}
              </div>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ font: "700 56px/1 'Roboto Condensed', monospace", minWidth: 60, textAlign: "center" }}>
              {d.home_score ?? "—"}
            </div>
            <Logo teamId={home.id} size={56} />
            <div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,.55)", letterSpacing: "0.14em", fontWeight: 700 }}>
                HOME
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, marginTop: 2 }}>{home.name}</div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,.5)" }}>SHOTS {d.home_shots ?? 0}</div>
            </div>
          </div>
        </div>

        {/* Period grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `1fr ${periodLabels.map(() => "70px").join(" ")} 70px`,
            borderTop: "1px solid rgba(255,255,255,.12)",
            textAlign: "center",
            fontSize: 11,
            fontWeight: 700,
            color: "rgba(255,255,255,.55)",
            letterSpacing: "0.10em",
          }}
        >
          <div style={{ padding: "10px 14px", textAlign: "left" }}>SCORING BY PERIOD</div>
          {periodLabels.map((p) => (
            <div key={p} style={{ padding: "10px 0" }}>
              {p}
            </div>
          ))}
          <div style={{ padding: "10px 0", color: "var(--gold)" }}>TOT</div>
        </div>
        {(["away", "home"] as const).map((side) => {
          const team = side === "away" ? away : home;
          const goals = side === "away" ? awayGoalsByPeriod : homeGoalsByPeriod;
          const total = side === "away" ? d.away_score : d.home_score;
          return (
            <div
              key={side}
              style={{
                display: "grid",
                gridTemplateColumns: `1fr ${periodLabels.map(() => "70px").join(" ")} 70px`,
                textAlign: "center",
                borderTop: "1px solid rgba(255,255,255,.12)",
                alignItems: "center",
              }}
            >
              <div style={{ padding: "10px 14px", textAlign: "left", display: "flex", alignItems: "center", gap: 8 }}>
                <Logo teamId={team.id} size={18} />
                <span style={{ fontSize: 13, fontWeight: 600 }}>{team.abbreviation}</span>
              </div>
              {periodLabels.map((_, i) => (
                <div key={i} style={{ padding: "10px 0", font: "700 16px/1 'Roboto Condensed', monospace" }}>
                  {goals[i]}
                </div>
              ))}
              <div style={{ padding: "10px 0", font: "800 18px/1 'Roboto Condensed', monospace", color: "var(--gold)" }}>
                {total ?? "—"}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 14, marginBottom: 14 }}>
        <Card title="Skater Stats">
          <Table>
            <thead>
              <tr>
                <Th>Player</Th>
                <Th className="num">G</Th>
                <Th className="num">A</Th>
                <Th className="num">PTS</Th>
                <Th className="num">SOG</Th>
              </tr>
            </thead>
            <tbody>
              {skaterPager.slice.map((s) => (
                <tr key={s.skater_id}>
                  <Td>
                    <Link to="/player/skater/$id" params={{ id: String(s.skater_id) }} style={{ fontWeight: 700, color: "var(--ink)" }}>
                      {s.skater_name}
                    </Link>
                  </Td>
                  <Td className="num">{s.goals}</Td>
                  <Td className="num">{s.assists}</Td>
                  <Td className="num">
                    <b>{s.goals + s.assists}</b>
                  </Td>
                  <Td className="num">{s.shots}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pagination {...skaterPager} onPage={skaterPager.setPage} />
        </Card>
        <Card title="Goaltending">
          <Table>
            <thead>
              <tr>
                <Th>Goalie</Th>
                <Th className="num">SA</Th>
                <Th className="num">SV</Th>
                <Th className="num">GA</Th>
                <Th className="num">SV%</Th>
              </tr>
            </thead>
            <tbody>
              {goaliePager.slice.map((s) => (
                <tr key={s.goalie_id}>
                  <Td>
                    <Link to="/player/goalie/$id" params={{ id: String(s.goalie_id) }} style={{ fontWeight: 700, color: "var(--ink)" }}>
                      {s.goalie_name}
                    </Link>
                  </Td>
                  <Td className="num">{s.shots_against}</Td>
                  <Td className="num">{s.saves}</Td>
                  <Td className="num">{s.goals_against}</Td>
                  <Td className="num">
                    <b>
                      {s.shots_against ? (s.saves / s.shots_against).toFixed(3).slice(1) : "—"}
                    </b>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pagination {...goaliePager} onPage={goaliePager.setPage} />
        </Card>
      </div>

      <Card title="Play-by-Play" sub={`${d.events.length} events`}>
        <div style={{ maxHeight: 480, overflow: "auto" }}>
          {eventPager.slice.map((e, i) => (
            <PlayRow
              key={eventPager.page * eventPager.pageSize + i}
              e={e}
              home={home}
              away={away}
              idx={i}
              last={i === eventPager.slice.length - 1}
            />
          ))}
        </div>
        <Pagination {...eventPager} onPage={eventPager.setPage} />
      </Card>
    </Shell>
  );
};

type Team = { id: number; abbreviation: string; name: string };
const PlayRow = ({
  e,
  home,
  away,
  idx,
  last,
}: {
  e: GameDetail["events"][number];
  home: Team;
  away: Team;
  idx: number;
  last: boolean;
}) => {
  const isHome = e.team_id === home.id;
  const team = isHome ? home : away;
  const big = e.kind === "goal";
  const iconColor = e.kind === "goal" ? "var(--green)" : e.kind === "penalty" ? "var(--red)" : "var(--bone)";
  const iconText =
    e.kind === "goal" ? "GOAL" : e.kind === "penalty" ? "PEN" : e.kind === "save" ? "SOG" : "SHT";
  const period = e.period > 3 ? "OT" : `P${e.period}`;
  const text =
    e.kind === "goal"
      ? `${e.primary_skater_name ?? "—"} scores${e.assist1_name ? ` (${e.assist1_name}${e.assist2_name ? `, ${e.assist2_name}` : ""})` : ""}${e.strength && e.strength !== "EV" ? ` · ${e.strength}` : ""}${e.shot_quality ? ` · ${e.shot_quality.toLowerCase()} chance` : ""}`
      : e.kind === "penalty"
      ? `${e.primary_skater_name ?? "—"} — ${(e.penalty_duration_ticks ?? 0) * 30}s minor`
      : e.kind === "save"
      ? `${e.primary_skater_name ?? "—"}, saved by ${e.goalie_name ?? "—"}`
      : `${e.primary_skater_name ?? "—"} — shot`;
  return (
    <div
      key={idx}
      style={{
        display: "grid",
        gridTemplateColumns: "60px 36px 24px 1fr",
        gap: 10,
        alignItems: "center",
        padding: "10px 16px",
        borderBottom: last ? "none" : "1px solid var(--line)",
        background: big ? "rgba(220,38,38,.06)" : "transparent",
      }}
    >
      <div style={{ font: "700 12px/1 'Roboto Condensed', monospace", color: "var(--ink-3)" }}>
        {period} · {e.tick}
      </div>
      <div
        style={{
          width: 32,
          height: 22,
          borderRadius: 4,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: iconColor,
          color: e.kind === "goal" || e.kind === "penalty" ? "#fff" : "var(--ink-3)",
          font: "800 9px/1 'Roboto Condensed', monospace",
          letterSpacing: "0.05em",
        }}
      >
        {iconText}
      </div>
      <Logo teamId={team.id} size={20} />
      <div style={{ fontSize: big ? 13 : 12, color: big ? "var(--ink)" : "var(--ink-2)", fontWeight: big ? 700 : 500 }}>
        {text}
        {e.strength === "EV" || !e.strength ? null : (
          <span className="tag" style={{ marginLeft: 8, background: "var(--bone)", color: "var(--ink-3)" }}>
            {e.strength}
          </span>
        )}
      </div>
    </div>
  );
};

export const Route = createFileRoute("/game/$gameId")({ component: Box });
