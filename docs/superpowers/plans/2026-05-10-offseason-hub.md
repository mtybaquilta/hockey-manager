# Offseason Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/offseason` hub page with a status-driven checklist that guides the user through offseason tasks before starting the next season.

**Architecture:** Pure frontend — all checklist status is derived from three existing queries (`useLeague`, `useRoster`, `useLineup`). One new route file. Dashboard gets a small CTA change. No backend changes.

**Tech Stack:** React, TypeScript, TanStack Router (file-based routes), TanStack Query, Tailwind/CSS custom properties.

---

## File map

| Action | File | Responsibility |
|---|---|---|
| Create | `frontend/src/routes/offseason.tsx` | Hub page — all checklist logic and UI |
| Modify | `frontend/src/routes/index.tsx` | Change offseason CTA to link to `/offseason` |
| Auto-updated | `frontend/src/routeTree.gen.ts` | Updated by TanStack Router Vite plugin on dev server start — do not edit manually |

---

## Task 1: Create `/offseason` route — skeleton with guard and loading state

**Files:**
- Create: `frontend/src/routes/offseason.tsx`

- [ ] **Step 1: Create the route file**

```tsx
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
```

- [ ] **Step 2: Start the dev server and verify the route registers**

```bash
cd /Users/jonas/Projects/hockey-manager/frontend && npm run dev
```

Open `http://localhost:5173/offseason` — should show "Loading…" or the placeholder text. Check that `routeTree.gen.ts` now includes an import for `./routes/offseason`. If not, save the file again to trigger the plugin.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/offseason.tsx frontend/src/routeTree.gen.ts
git commit -m "feat(offseason): scaffold /offseason route with guard"
```

---

## Task 2: Add checklist status helpers and render checklist rows

**Files:**
- Modify: `frontend/src/routes/offseason.tsx`

These helpers go at the top of the file, before the component. They are pure functions with no side effects.

- [ ] **Step 1: Add the status type, helpers, and config above the component**

The 20 lineup slot keys (exact names from `LineupSlots` in `frontend/src/api/types.ts`):

```tsx
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
  const expSkaters = roster.skaters.filter(
    (s) => s.contract?.expires_after_year === year
  ).length;
  const expGoalies = roster.goalies.filter(
    (g) => g.contract?.expires_after_year === year
  ).length;
  return expSkaters + expGoalies;
}

const STATUS_META: Record<CheckStatus, { color: string; icon: string; label: string }> = {
  action:      { color: "var(--red)",    icon: "●", label: "Action needed" },
  warning:     { color: "var(--amber)",  icon: "⚠", label: "Warning" },
  recommended: { color: "var(--ice)",    icon: "→", label: "Recommended" },
  complete:    { color: "var(--green)",  icon: "✓", label: "Complete" },
  optional:    { color: "var(--ink-3)", icon: "·", label: "Optional" },
};
```

- [ ] **Step 2: Add the `StatusBadge` and `CheckRow` sub-components below the helpers**

```tsx
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
        minWidth: 120,
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
  to: string;
  params?: Record<string, string>;
  title: string;
  sub?: string;
}) => (
  <Link
    to={to}
    params={params}
    style={{ textDecoration: "none", color: "inherit" }}
  >
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
```

- [ ] **Step 3: Replace the placeholder body in `OffseasonHub` with the computed checklist**

Replace the `<p>Placeholder checklist</p>` block with:

```tsx
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
          sub="See how your players developed last season"
        />
        <CheckRow
          status={expiringCount > 0 ? "warning" : "complete"}
          to={`/team/${teamIdStr}`}
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
    </Shell>
  );
```

Note: the `return` at the bottom of the component needs to be removed since we're adding the return inside the component body. The full component body should not have two `return` statements — remove the old placeholder return.

- [ ] **Step 4: Verify in browser**

Navigate to `/offseason` (you may need to manually go there during regular season in dev). The checklist card should render 5 rows with color-coded badges and sub-text.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/offseason.tsx
git commit -m "feat(offseason): checklist rows with status badges"
```

---

## Task 3: Add "Start Next Season" action block

**Files:**
- Modify: `frontend/src/routes/offseason.tsx`

- [ ] **Step 1: Add the action block below the checklist card**

After the closing `</div>` of the checklist `.card`, add:

```tsx
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
```

- [ ] **Step 2: Verify in browser**

With an empty lineup slot present: button should be disabled, red message shown. With all slots filled: button should be enabled.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/offseason.tsx
git commit -m "feat(offseason): start next season action with lineup guard"
```

---

## Task 4: Update dashboard offseason CTA

**Files:**
- Modify: `frontend/src/routes/index.tsx`

- [ ] **Step 1: Locate the offseason button in the dashboard**

In `frontend/src/routes/index.tsx`, find the block around line 93–106 that renders the offseason `<button>` (it currently calls `startNext.mutate`):

```tsx
        ) : inOffseason ? (
          <button
            className="btn btn-primary"
            disabled={startNext.isPending}
            onClick={() =>
              startNext.mutate(undefined, {
                onSuccess: (res) => nav({ to: "/development-summary", search: { season_id: res.new_season_id } }),
              })
            }
          >
            {startNext.isPending ? "Starting…" : "Start New Season →"}
          </button>
```

- [ ] **Step 2: Replace that button with a Link to the hub**

```tsx
        ) : inOffseason ? (
          <Link to="/offseason" className="btn btn-primary">
            Offseason Hub →
          </Link>
```

`Link` is already imported at the top of `index.tsx`.

- [ ] **Step 3: Remove the now-unused `useStartNextSeason` import from `index.tsx`**

The dashboard no longer calls `startNext`, so remove:
```tsx
import { useStartNextSeason } from "../queries/development";
```
and remove the `const startNext = useStartNextSeason();` line.

- [ ] **Step 4: Update the offseason banner copy**

Find the offseason banner card around line 117–132:

```tsx
      {inOffseason && (
        <div
          className="card"
          style={{
            padding: "14px 18px",
            marginBottom: 14,
            borderLeft: "3px solid #b45309",
            background: "rgba(245, 158, 11, 0.08)",
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Offseason</div>
          <div style={{ fontSize: 13, color: "var(--ink-2)" }}>
            The season is over. Sign free agents, then start the next season when you're ready.
          </div>
        </div>
      )}
```

Update the body text to reference the hub:

```tsx
      {inOffseason && (
        <div
          className="card"
          style={{
            padding: "14px 18px",
            marginBottom: 14,
            borderLeft: "3px solid #b45309",
            background: "rgba(245, 158, 11, 0.08)",
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Offseason</div>
          <div style={{ fontSize: 13, color: "var(--ink-2)" }}>
            The season is over. Use the Offseason Hub to review contracts, sign free agents, and set your lineup before starting the next season.
          </div>
        </div>
      )}
```

- [ ] **Step 5: Verify in browser**

Trigger offseason via the dev sim-forward tool (sim to end of playoffs). The dashboard should show the banner with updated copy and the top-right CTA should say "Offseason Hub →" and navigate to `/offseason`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/index.tsx
git commit -m "feat(offseason): update dashboard CTA to link to Offseason Hub"
```
