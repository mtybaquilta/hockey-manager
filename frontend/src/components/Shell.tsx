import { Link, useLocation } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { useLeague } from "../queries/league";
import { useStandings } from "../queries/standings";
import { useTeams } from "../queries/teams";
import { Logo } from "./Logo";

const NAV: { id: string; label: string; to: string; icon: string; match: (p: string) => boolean }[] = [
  { id: "dashboard", label: "Dashboard", to: "/", icon: "M3 12L12 4l9 8M5 10v10h14V10", match: (p) => p === "/" },
  { id: "schedule", label: "Schedule", to: "/schedule", icon: "M3 7h18M3 7v12a1 1 0 001 1h16a1 1 0 001-1V7M3 7l1-3h16l1 3M8 11v4m4-4v4m4-4v4", match: (p) => p.startsWith("/schedule") || p.startsWith("/game") },
  { id: "standings", label: "Standings", to: "/standings", icon: "M4 20V10m6 10V4m6 16v-7", match: (p) => p.startsWith("/standings") },
  { id: "team", label: "My Team", to: "/team", icon: "M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0", match: (p) => p.startsWith("/team") && !p.endsWith("/lineup") },
  { id: "lineup", label: "Lineup", to: "/lineup", icon: "M3 5h18M3 12h18M3 19h18", match: (p) => p.endsWith("/lineup") },
  { id: "stats", label: "Stats", to: "/stats", icon: "M4 20V10m6 10V4m6 16v-7m6 7v-12", match: (p) => p.startsWith("/stats") || p.startsWith("/player") },
];

export const Shell = ({
  children,
  crumbs = [],
  topRight,
}: {
  children: ReactNode;
  crumbs?: string[];
  topRight?: ReactNode;
}) => {
  const league = useLeague();
  const teams = useTeams();
  const standings = useStandings();
  const loc = useLocation();
  const userId = league.data?.user_team_id ?? null;
  const me = userId != null ? teams.data?.find((t) => t.id === userId) : undefined;
  const myRow = userId != null ? standings.data?.rows.find((r) => r.team_id === userId) : undefined;
  const teamHref = userId != null ? `/team/${userId}` : "/";
  const lineupHref = userId != null ? `/team/${userId}/lineup` : "/";
  const matchday = league.data?.current_matchday ?? 0;

  const hrefFor = (id: string) =>
    id === "team"
      ? teamHref
      : id === "lineup"
      ? lineupHref
      : NAV.find((n) => n.id === id)!.to;

  return (
    <div className="chl-shell">
      <aside className="chl-side">
        <div className="chl-brand">
          <div className="chl-brand-mark"></div>
          <div className="chl-brand-text">
            <b>CHL</b>
            <br />
            <small>Manager '26</small>
          </div>
        </div>
        {me && (
          <div className="chl-team-card">
            <Logo teamId={me.id} size={36} />
            <div className="meta">
              <b>{me.name}</b>
              <small>
                {myRow
                  ? `${myRow.wins}-${myRow.losses}-${myRow.ot_losses}`
                  : me.abbreviation}
              </small>
            </div>
          </div>
        )}
        <nav className="chl-nav">
          <div className="chl-nav-section">Manage</div>
          {NAV.map((n) => {
            const active = n.match(loc.pathname);
            return (
              <Link key={n.id} to={hrefFor(n.id)} className={active ? "active" : ""}>
                <svg
                  className="ic"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d={n.icon} />
                </svg>
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="chl-side-foot">
          <span>Matchday {matchday}</span>
          <b>'25-26</b>
        </div>
      </aside>
      <div className="chl-main">
        <div className="chl-topbar">
          <div className="chl-crumbs">
            {crumbs.map((c, i) => (
              <span key={i} style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                {i > 0 && <span>/</span>}
                {i === crumbs.length - 1 ? <b>{c}</b> : c}
              </span>
            ))}
          </div>
          <div className="grow"></div>
          <span className="chl-pill">
            <span className="dot"></span>
            {league.data?.status === "complete" ? "SEASON COMPLETE" : `MATCHDAY ${matchday}`}
          </span>
          {topRight}
        </div>
        <div className="chl-content">{children}</div>
      </div>
    </div>
  );
};
