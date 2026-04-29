import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Card } from "../components/Card";
import { Logo } from "../components/Logo";
import { Pagination, usePager } from "../components/Pagination";
import { ResultBadge } from "../components/ResultBadge";
import { Shell } from "../components/Shell";
import { useLeague } from "../queries/league";
import { useSchedule } from "../queries/schedule";
import { useTeams } from "../queries/teams";

const SchedulePage = () => {
  const sched = useSchedule();
  const league = useLeague();
  const teams = useTeams();
  const nav = useNavigate();
  if (!sched.data || !league.data || !teams.data) {
    return <Shell crumbs={["Continental Hockey League", "Schedule"]}>Loading…</Shell>;
  }
  const userId = league.data.user_team_id;
  const games = userId == null ? sched.data.games : sched.data.games.filter((g) => g.home_team_id === userId || g.away_team_id === userId);
  const past = games.filter((g) => g.status === "simulated");
  const upcoming = games.filter((g) => g.status === "scheduled");
  // Past list is reversed (most recent first); pager works on the reversed array.
  const pastReversed = past.slice().reverse();
  const pastPager = usePager(pastReversed);
  const upcomingPager = usePager(upcoming);

  const teamName = (id: number) => teams.data!.find((t) => t.id === id)?.name ?? "—";
  const teamAbbr = (id: number) => teams.data!.find((t) => t.id === id)?.abbreviation ?? "—";

  const PastRow = ({ g }: { g: (typeof games)[number] }) => {
    const meIsHome = userId != null && g.home_team_id === userId;
    const oppId = userId == null ? g.away_team_id : meIsHome ? g.away_team_id : g.home_team_id;
    const myScore = userId == null ? g.home_score : meIsHome ? g.home_score : g.away_score;
    const oppScore = userId == null ? g.away_score : meIsHome ? g.away_score : g.home_score;
    const won = (myScore ?? 0) > (oppScore ?? 0);
    const dotColor = userId == null
      ? "var(--ink-3)"
      : g.result_type === "OT" || g.result_type === "SO"
      ? "var(--gold)"
      : won
      ? "var(--green)"
      : "var(--red)";
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "90px 24px 1fr auto auto",
          gap: 14,
          alignItems: "center",
          padding: "12px 18px",
          borderBottom: "1px solid var(--line)",
          cursor: "pointer",
        }}
        onClick={() => nav({ to: "/game/$gameId", params: { gameId: String(g.id) } })}
      >
        <div style={{ fontSize: 11, color: "var(--ink-3)", fontWeight: 600 }}>MD {g.matchday}</div>
        <div
          style={{
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: dotColor,
            border: "2px solid var(--paper)",
            boxShadow: "0 0 0 1px var(--line)",
          }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {userId != null && (
            <span
              style={{
                fontSize: 11,
                color: "var(--ink-4)",
                fontWeight: 700,
                letterSpacing: "0.10em",
              }}
            >
              {meIsHome ? "VS" : "@"}
            </span>
          )}
          <Logo teamId={oppId} size={26} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{teamName(oppId)}</div>
            <div style={{ fontSize: 11, color: "var(--ink-3)" }}>{teamAbbr(oppId)}</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
          <span
            style={{
              font: "700 22px/1 'Roboto Condensed', monospace",
              color: won ? "var(--ink)" : "var(--ink-3)",
            }}
          >
            {myScore}
          </span>
          <span style={{ color: "var(--ink-4)" }}>–</span>
          <span
            style={{
              font: "700 22px/1 'Roboto Condensed', monospace",
              color: !won ? "var(--ink)" : "var(--ink-3)",
            }}
          >
            {oppScore}
          </span>
          <ResultBadge type={g.result_type} />
        </div>
        <a className="link" style={{ fontSize: 11, color: "var(--navy-600)", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>
          Recap →
        </a>
      </div>
    );
  };

  const UpcomingRow = ({ g }: { g: (typeof games)[number] }) => {
    const meIsHome = userId != null && g.home_team_id === userId;
    const oppId = userId == null ? g.away_team_id : meIsHome ? g.away_team_id : g.home_team_id;
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "90px 24px 1fr auto",
          gap: 14,
          alignItems: "center",
          padding: "12px 18px",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div style={{ fontSize: 11, color: "var(--ink-3)", fontWeight: 600 }}>MD {g.matchday}</div>
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: "var(--surface)",
            border: "2px solid var(--ink-4)",
            marginLeft: 2,
          }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {userId != null && (
            <span
              style={{
                fontSize: 11,
                color: "var(--ink-4)",
                fontWeight: 700,
                letterSpacing: "0.10em",
              }}
            >
              {meIsHome ? "VS" : "@"}
            </span>
          )}
          <Logo teamId={oppId} size={26} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{teamName(oppId)}</div>
            <div style={{ fontSize: 11, color: "var(--ink-3)" }}>
              {teamAbbr(oppId)} · {userId != null && (meIsHome ? "Home" : "Away")}
            </div>
          </div>
        </div>
        <span className="tag tag-final">Scheduled</span>
      </div>
    );
  };

  return (
    <Shell crumbs={["Continental Hockey League", "Schedule"]}>
      <div className="section-h">
        <h1>Schedule</h1>
        <span className="sub">
          {past.length} played · {upcoming.length} remaining
        </span>
      </div>

      <Card className="!p-0">
        <div
          style={{
            padding: "10px 18px 6px 18px",
            fontSize: 10,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "var(--ink-3)",
            fontWeight: 700,
            background: "var(--bone)",
            borderBottom: "1px solid var(--line)",
          }}
        >
          Recent
        </div>
        {past.length === 0 && (
          <div style={{ padding: 20, textAlign: "center", color: "var(--ink-4)", fontSize: 12 }}>
            No games played yet.
          </div>
        )}
        {pastPager.slice.map((g) => (
          <PastRow key={g.id} g={g} />
        ))}
        <Pagination {...pastPager} onPage={pastPager.setPage} />

        <div
          style={{
            padding: "10px 18px 6px 18px",
            fontSize: 10,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "var(--ink-3)",
            fontWeight: 700,
            background: "var(--bone)",
            borderTop: "1px solid var(--line)",
            borderBottom: "1px solid var(--line)",
          }}
        >
          Upcoming
        </div>
        {upcoming.length === 0 && (
          <div style={{ padding: 20, textAlign: "center", color: "var(--ink-4)", fontSize: 12 }}>
            No upcoming games.
          </div>
        )}
        {upcomingPager.slice.map((g) => (
          <UpcomingRow key={g.id} g={g} />
        ))}
        <Pagination {...upcomingPager} onPage={upcomingPager.setPage} />
      </Card>
    </Shell>
  );
};

export const Route = createFileRoute("/schedule")({ component: SchedulePage });
