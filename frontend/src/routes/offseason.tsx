import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Shell } from "../components/Shell";
import { useLeague } from "../queries/league";
import { useRoster } from "../queries/teams";
import { useLineup } from "../queries/lineup";
import { useStartNextSeason } from "../queries/development";
import type { Lineup, LineupSlots, Roster } from "../api/types";

// ── Status helpers ────────────────────────────────────────────────────────────

type CheckStatus = "recommended" | "warning" | "action" | "complete" | "optional";

const LINEUP_SLOT_KEYS: (keyof LineupSlots)[] = [
  "line1_lw_id", "line1_c_id", "line1_rw_id",
  "line2_lw_id", "line2_c_id", "line2_rw_id",
  "line3_lw_id", "line3_c_id", "line3_rw_id",
  "line4_lw_id", "line4_c_id", "line4_rw_id",
  "pair1_ld_id", "pair1_rd_id",
  "pair2_ld_id", "pair2_rd_id",
  "pair3_ld_id", "pair3_rd_id",
  "starting_goalie_id", "backup_goalie_id",
];

function countEmptySlots(lineup: Lineup): number {
  return LINEUP_SLOT_KEYS.filter((k) => lineup[k] == null).length;
}

function countExpiringContracts(roster: Roster, year: number): number {
  return (
    roster.skaters.filter((s) => s.contract?.expires_after_year === year).length +
    roster.goalies.filter((g) => g.contract?.expires_after_year === year).length
  );
}

const STATUS_META: Record<CheckStatus, { color: string; icon: string; label: string }> = {
  action:      { color: "var(--red)",    icon: "●", label: "Action needed" },
  warning:     { color: "var(--amber)",  icon: "⚠", label: "Warning" },
  recommended: { color: "var(--ice)",    icon: "→", label: "Recommended" },
  complete:    { color: "var(--green)",  icon: "✓", label: "Complete" },
  optional:    { color: "var(--ink-3)", icon: "·", label: "Optional" },
};

// ── Sub-components ────────────────────────────────────────────────────────────

const StatusBadge = ({ status }: { status: CheckStatus }) => {
  const m = STATUS_META[status];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: "0.08em",
        color: m.color,
        minWidth: 130,
      }}
    >
      <span style={{ fontSize: 13 }}>{m.icon}</span>
      {m.label.toUpperCase()}
    </span>
  );
};

const CheckRow = ({
  status,
  to,
  params,
  title,
  sub,
}: {
  status: CheckStatus;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  to: any;
  params?: Record<string, string>;
  title: string;
  sub?: string;
}) => (
  <Link to={to} params={params} style={{ textDecoration: "none", color: "inherit" }}>
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "14px 18px",
        borderBottom: "1px solid var(--line)",
        cursor: "pointer",
        transition: "background 0.1s",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.03)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "")}
    >
      <StatusBadge status={status} />
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: 14 }}>{title}</div>
        {sub && <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 2 }}>{sub}</div>}
      </div>
      <span style={{ color: "var(--ink-4)", fontSize: 13 }}>→</span>
    </div>
  </Link>
);

// ── Page ──────────────────────────────────────────────────────────────────────

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

  const year = league.data.year;
  const emptySlots = countEmptySlots(lineup.data);
  const expiringCount = countExpiringContracts(roster.data, year);
  const skaterCount = roster.data.skaters.length;
  const goalieCount = roster.data.goalies.length;
  const teamIdStr = String(userTeamId);

  return (
    <Shell crumbs={["Continental Hockey League", "Offseason Hub"]}>
      <div className="section-h">
        <h1>Offseason Hub</h1>
        <span className="sub">
          {roster.data.team.name} · Year {year}
        </span>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <CheckRow
          status="recommended"
          to="/development-summary"
          title="Review development summary"
          sub="Player progressions from the last rollover"
        />
        <CheckRow
          status={expiringCount > 0 ? "warning" : "complete"}
          to="/team/$teamId"
          params={{ teamId: teamIdStr }}
          title="Review expiring contracts"
          sub={
            expiringCount > 0
              ? `${expiringCount} contract${expiringCount > 1 ? "s" : ""} expire this year`
              : "No contracts expiring"
          }
        />
        <CheckRow
          status={skaterCount < 18 || goalieCount < 2 ? "warning" : "recommended"}
          to="/free-agents"
          title="Manage free agents"
          sub={`${skaterCount} skaters · ${goalieCount} goalies on roster`}
        />
        <CheckRow
          status="optional"
          to="/trades"
          title="Explore trades"
          sub="Propose trades with other teams"
        />
        <CheckRow
          status={emptySlots > 0 ? "action" : "complete"}
          to="/team/$teamId/lineup"
          params={{ teamId: teamIdStr }}
          title="Fix lineup"
          sub={
            emptySlots > 0
              ? `${emptySlots} empty slot${emptySlots > 1 ? "s" : ""} — must be filled before next season`
              : "All lineup slots filled"
          }
        />
      </div>

      <div
        className="card"
        style={{
          padding: "20px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>Start Next Season</div>
          {emptySlots > 0 ? (
            <div style={{ fontSize: 12, color: "var(--red)", marginTop: 4 }}>
              Fill all lineup slots before starting
            </div>
          ) : (
            <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 4 }}>
              Lineup is complete — ready to go
            </div>
          )}
        </div>
        <button
          className="btn btn-primary"
          disabled={emptySlots > 0 || startNext.isPending}
          onClick={() =>
            startNext.mutate(undefined, {
              onSuccess: (res) => {
                nav({ to: "/development-summary", search: { season_id: res.new_season_id } });
              },
            })
          }
        >
          {startNext.isPending ? "Starting…" : "Start Next Season →"}
        </button>
      </div>
    </Shell>
  );
};

export const Route = createFileRoute("/offseason")({ component: OffseasonHub });
