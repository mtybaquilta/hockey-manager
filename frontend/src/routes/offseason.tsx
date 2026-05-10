import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Shell } from "../components/Shell";
import { useLeague } from "../queries/league";
import { useRoster } from "../queries/teams";
import { useLineup } from "../queries/lineup";
import { useStartNextSeason } from "../queries/development";
import type { Lineup, LineupSlots, Roster } from "../api/types";

const OffseasonHub = () => {
  const league = useLeague();
  const nav = useNavigate();
  const userTeamId = league.data?.user_team_id ?? null;
  const roster = useRoster(userTeamId ?? 0);
  const lineup = useLineup(userTeamId ?? 0);
  const startNext = useStartNextSeason();

  // Guard: only valid during offseason
  useEffect(() => {
    if (league.data && league.data.phase !== "offseason") {
      nav({ to: "/" });
    }
  }, [league.data, nav]);

  if (!league.data || !roster.data || !lineup.data || userTeamId == null) {
    return (
      <Shell crumbs={["Continental Hockey League", "Offseason Hub"]}>
        Loading…
      </Shell>
    );
  }

  return (
    <Shell crumbs={["Continental Hockey League", "Offseason Hub"]}>
      <div className="section-h">
        <h1>Offseason Hub</h1>
        <span className="sub">
          {roster.data.team.name} · Year {league.data.year}
        </span>
      </div>
      <p style={{ color: "var(--ink-2)", marginBottom: 18 }}>
        Placeholder checklist
      </p>
    </Shell>
  );
};

export const Route = createFileRoute("/offseason")({ component: OffseasonHub });
