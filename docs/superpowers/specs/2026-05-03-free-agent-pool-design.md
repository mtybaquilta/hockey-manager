# P1.1 — Free Agent Pool Design

Date: 2026-05-03
Phase: 6 (Roster Agency — first slice)

## Goal

Let the user act on their roster externally: browse a seeded pool of free-agent
players, sign them to the user-controlled team, and release rostered players
back to the pool. End-to-end vertical slice. No contracts, salary cap, trades,
draft, scouting, or AI signings.

Gameplay loop this enables:

    Inspect weakness → find FA → sign → adjust lineup → sim → evaluate

## Scope (in)

- Seeded FA pool generated once at league/season creation.
- `GET /free-agents/skaters` and `GET /free-agents/goalies` with filtering and sorting.
- Sign FA → user team. Release rostered player → FA pool.
- Release auto-clears any lineup slots referencing the released player.
- `/free-agents` page in the frontend with filter/sort UI and a Sign button per row.
- Release button on the existing team page (user team only), with a confirm modal.

## Scope (out — explicitly deferred)

- AI signings by the other 3 teams.
- Roster size limits (lineup validation remains the only gate).
- Transfer windows / preseason-only restrictions.
- Player roles, archetypes (display layer or schema).
- Salary cap, contracts, trades, draft, scouting, waivers.
- Frontend automated tests for this page.

## Decisions Locked During Brainstorm

| # | Decision |
|---|---|
| Q1 | P1.1 = pool + sign + release (full vertical slice). |
| Q2 | Seeded pool at league creation; released players flow back in. |
| Q3 | No roster size limits in P1.1. |
| Q4 | Compute OVR on read; no Role/Archetype columns in P1.1. |
| Q5 | `team_id` nullable; `team_id IS NULL` ⇔ free agent. |
| Q6 | ~40 skaters + 5 goalies; bell curve; 1–2 gems. |
| Q7 | Sign instant (no modal); release confirms via modal. |
| Q8 | Single user-controlled team; reuse existing `season.user_team_id`. |
| Q10 | Release auto-clears lineup slots; stats persist on the player. |
| Q11 | Sign/release available any time. |

## Architecture

- Generation logic: extends `app/services/generation/` (reuses `_attr`,
  `_skater_overall`, `_potential_for`, `_pick_dev_type`, `make_player_name`).
  Keeps the sim package free of FA-specific code.
- Service layer: `app/services/free_agents_service.py` — list/sign/release
  functions. All authorization checks live here (user-team gate).
- API: `app/api/free_agents.py` — thin handlers, delegate to the service.
- Schemas: `app/schemas/free_agents.py` — Pydantic models with computed `ovr`.
- Frontend: new `/free-agents` page; release button on the existing team page.
- No changes inside `backend/sim/` — FA status is irrelevant to the simulator.

## Data Model

Migration: `phase6_free_agency` (Alembic).

- `skater.team_id`: drop `NOT NULL`. FK changes from `ON DELETE CASCADE` to
  `ON DELETE SET NULL`. Index retained.
- `goalie.team_id`: same treatment.
- No new columns. No new tables. No backfill required (existing rows have
  non-null team_ids).

Invariant: `team_id IS NULL` ⇔ free agent. Enforced by service-layer query
filters; never via a separate boolean or status column.

Lineup slots, stats rows, and game events keep their existing FKs to
skater/goalie. They remain valid when a player is unsigned (and continue to
behave correctly if the player is later re-signed).

## Pool Generation

New module: `app/services/generation/free_agents.py`. Called once at
league/season creation, immediately after `generate_players_for_team` runs for
all 4 teams (so it shares the `used_names` set).

Counts:

- 40 skaters: 8 LW, 8 C, 8 RW, 8 LD, 8 RD.
- 5 goalies.

Attribute distribution (lower than rostered baseline so signings are usually
trade-offs, not free wins):

- `_fa_attr(rng) = clamp(int(rng.gauss(63, 7)), 40, 88)`
- `_fa_goalie_attr(rng) = clamp(int(rng.gauss(68, 6)), 45, 88)`

Gem injection (post-generation): pick 2 random FA skaters and 1 random FA
goalie; for each, add `rng.randint(8, 14)` to every attribute and re-clamp.
Re-derive OVR via existing `_skater_overall` / `_goalie_overall`.

Age ranges match rostered generation: skaters 19–35, goalies 20–36.

Determinism: uses the existing `season.seed`. Same seed → identical pool.

Released players flow back implicitly: the release endpoint nulls `team_id`
on an existing row; that row immediately appears in FA queries.

## API

All routes registered in `app/api/__init__.py`.

### Listing

- `GET /free-agents/skaters`
  - Query params (all optional): `position` (LW|C|RW|LD|RD), `min_ovr` (int),
    `min_potential` (int), `max_age` (int), `sort` (`ovr`|`potential`|`age`|`position`,
    default `ovr`), `order` (`asc`|`desc`, default `desc`).
  - Returns `list[FreeAgentSkaterOut]`. Filtered to `team_id IS NULL`.
- `GET /free-agents/goalies`
  - Same query params except `position` is omitted. Returns
    `list[FreeAgentGoalieOut]`.

### Sign / release

- `POST /teams/{team_id}/sign/skater/{skater_id}`
- `POST /teams/{team_id}/sign/goalie/{goalie_id}`
- `POST /teams/{team_id}/release/skater/{skater_id}`
- `POST /teams/{team_id}/release/goalie/{goalie_id}`

All return the updated player (`SkaterOut` / `GoalieOut`).

### Errors

- 403 if `team_id != season.user_team_id`.
- 404 if player not found.
- 400 on sign if `player.team_id IS NOT NULL` (already signed).
- 400 on release if `player.team_id != team_id` (not on this team).

### Side effects

- Sign: set `player.team_id = team_id`. Commit.
- Release: set `player.team_id = NULL`; delete any `lineup_slot` rows
  referencing the player. Stats rows untouched. Commit.

## Frontend

New route `/free-agents`, linked from the top nav.

Page: `frontend/src/pages/FreeAgentsPage.tsx`. Two tabs/sections — Skaters and
Goalies.

Filter bar:

- Position dropdown (skaters only): All / LW / C / RW / LD / RD.
- Min OVR (numeric, 50–90).
- Min Potential (numeric).
- Max Age (numeric).
- Sort dropdown: OVR / Potential / Age / Position.
- Order: asc / desc.

Filters and sort live in component state. Each change refetches via TanStack
Query (query key includes all filter values).

Skater table columns: Name, Age, Pos, OVR, POT, SKA, SHO, PAS, DEF, PHY, Sign.
Goalie table columns: Name, Age, OVR, POT, REF, POS, REB, PUC, MEN, Sign.

Sign click → `POST /teams/{userTeamId}/sign/...` → invalidate
`['free-agents']` and `['teams', userTeamId]` queries → toast.

Release lives on the existing team page. Per-row Release button visible only
when viewing the user team. Click → confirm modal "Release {name}? They'll
become a free agent." → `POST /teams/{userTeamId}/release/...` → invalidate →
toast.

User-team awareness: read `season.user_team_id` from the existing season
endpoint. If absent, show an inline notice on `/free-agents` and disable Sign
buttons.

## Testing

Backend (`backend/tests/`):

- `test_free_agent_generation.py`
  - Pool size: 40 skaters + 5 goalies after league creation.
  - Position distribution: 8 per skater position.
  - Determinism: same seed → identical (id-ordered) snapshot.
  - OVR distribution sanity: mean inside expected band; ≥1 gem at OVR ≥ 75.
  - No name collisions with rostered players.
- `test_free_agents_api.py`
  - List returns only `team_id IS NULL` rows.
  - Filters: position, min_ovr, min_potential, max_age narrow correctly;
    combinations work.
  - Sort: default OVR desc; alternative keys and orders work.
  - Goalie endpoint mirrors skater behavior.
- `test_sign_release_api.py`
  - Sign: player joins team; subsequent FA list excludes them.
  - Sign rejected (403) for non-user team.
  - Sign rejected (400) when player already signed.
  - Release: player becomes FA; lineup slots cleared; stats rows preserved.
  - Release rejected (403) for non-user team.
  - Release rejected (400) when player not on that team.
  - Round-trip: sign → release → re-sign keeps id and prior stats.

Frontend: no new automated tests in P1.1 (matches current scope). Manual
verification of filter/sort/sign/release flow during implementation.

## Documentation Updates

- `docs/product-scope.md`: add "Free Agents" under In Scope; note nullable
  `team_id`.
- `docs/not-now.md`: remove "Free agency" line, or annotate "P1.1 implemented;
  deeper systems still deferred."
- `docs/phase-6.md`: new file describing this slice (matches the
  `phase-2.md` precedent and the migration name `phase6_free_agency`).

## Open Questions

None — all resolved during brainstorm.
