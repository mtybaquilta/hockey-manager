# Offseason Hub — Design Spec

Date: 2026-05-10

## Goal

A guided offseason page that helps the user understand what to do before starting the next season. Replaces the inline offseason banner on the dashboard as the primary offseason UI.

## Route

`/offseason`

Accessible only when `league.phase === "offseason"`. If the user navigates there outside of offseason, redirect to `/`.

## Navigation changes (dashboard)

When `inOffseason`:
- The existing inline "Start New Season →" button is replaced with "Offseason Hub →" linking to `/offseason`.
- The offseason banner body can remain for context but the primary CTA points to the hub.

## Data sources (frontend-only, no new endpoints)

| Hook | Used for |
|---|---|
| `useLeague()` | `year`, `user_team_id`, `phase` |
| `useRoster(userTeamId)` | contract expiry counts, roster size |
| `useLineup(userTeamId)` | null slot count |

## Checklist items

### 1. Development Summary
- **Link:** `/development-summary`
- **Status:** always `recommended`
- **Label:** "Review player development from last season"

### 2. Expiring Contracts
- **Link:** `/team/$teamId` (roster view shows contract badges)
- **Status logic:**
  - `warning` if any rostered player has `contract.expires_after_year === year`
  - `complete` if none
- **Label:** "Review expiring contracts" — show count of expiring contracts when in warning state

### 3. Manage Free Agents
- **Link:** `/free-agents`
- **Status logic:**
  - `warning` if `skaters.length < 18 || goalies.length < 2`
  - `recommended` if roster is healthy
- **Label:** "Sign or release players" — show roster counts (e.g. "16 skaters · 2 goalies")

### 4. Explore Trades
- **Link:** `/trades`
- **Status:** always `optional`
- **Label:** "Explore trades with other teams"

### 5. Fix / Refill Lineup
- **Link:** `/team/$teamId/lineup`
- **Status logic:**
  - `action` if any of the 20 lineup slots is null
  - `complete` if all slots filled
- **Label:** "Set your lineup for next season" — show empty slot count when in action state

### 6. Start Next Season
- Not a checklist row — a standalone action at the bottom of the page.
- **State: blocked** if any lineup slot is null → button is disabled, shows reason ("Fill all lineup slots first")
- **State: ready** if lineup is full → button enabled, calls `useStartNextSeason()`, navigates to `/development-summary` on success (same as current behaviour)

## Status badge design

Five states rendered as a small pill/icon to the left of each row:

| State | Visual |
|---|---|
| `complete` | green ✓ |
| `action` | red ● (filled dot) |
| `warning` | amber ⚠ |
| `recommended` | blue → |
| `optional` | gray · |

## Page layout

```
[Shell crumbs: CHL > Offseason Hub]

Header: "Offseason · Year {year}" + team name

Checklist card:
  Row 1 — [badge] Development Summary           →
  Row 2 — [badge] Expiring Contracts             →
  Row 3 — [badge] Manage Free Agents             →
  Row 4 — [badge] Explore Trades                 →
  Row 5 — [badge] Fix / Refill Lineup            →

Footer:
  [Start Next Season] button — disabled/ready based on lineup
```

Each row is a full-width clickable link. Sub-text shows contextual detail (e.g. "3 contracts expiring", "2 empty slots").

## What is NOT included

- No auto-redirect from dashboard to hub (user navigates explicitly via CTA).
- No draft, scouting, salary cap, morale, or injury items.
- No backend changes.
- No "mark as viewed" persistence — status is always derived from live data.
