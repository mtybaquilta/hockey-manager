# 4-Team Mini-Season MVP — Design Spec

**Date:** 2026-04-26
**Phase:** 1 — Tiny Playable League
**Status:** Approved design, pending implementation plan

## 1. Goal & Scope

Build a playable 4-team mini-season that proves the core manager loop:

```
View team → Set lineup → Simulate next game/day → Inspect result/stats → Advance
```

The user manages **one** team. "Advance" simulates the user's next game and all
other games on the same matchday atomically.

In scope: one league, 4 procedurally generated teams (~20 players each),
deterministic event-driven game simulation, basic standings (with OTL),
roster/lineup/schedule/box-score/standings UI, season-complete screen.

Out of scope (deferred to `docs/not-now.md`): trades, draft, contracts, cap,
injuries, scouting, playoffs, multi-save, auth, advanced tactics, chemistry,
realtime visualization.

Single active league/save. No auth. No multi-save.

## 2. Architecture

Strict layering. **Sim never touches Postgres. Postgres never touches sim.
Services are the only bridge.**

```
React (frontend/)
   │  HTTP/JSON
FastAPI route (backend/app/api/)
   │
Service / workflow (backend/app/services/)
   ├──► Repository (backend/app/repositories/) ──► SQLAlchemy ──► Postgres
   └──► Pure sim (backend/sim/) — dataclasses in / dataclasses out
```

Sim has zero dependency on FastAPI, SQLAlchemy, requests, env vars, wall-clock,
or external services. It receives all input explicitly and is deterministic for
a given `(input, seed)`.

### Repo layout

```
frontend/                React + Vite + TS app
backend/
  app/
    api/                 FastAPI routes (thin)
    services/            workflows: advance_matchday, create_league, ...
    repositories/        SQLAlchemy queries
    models/              SQLAlchemy ORM models
    schemas/             Pydantic request/response
  sim/
    engine.py            simulate_game(input) -> result
    models.py            frozen dataclasses
    ratings.py
  alembic/
  data/                  JSON name pools (teams, first/last names)
  tests/
  pyproject.toml         (uv-managed)
docs/
```

Tooling: **uv** for Python deps, Alembic for migrations, pytest for tests.

## 3. Data Model (SQLAlchemy)

All IDs are integer surrogate keys. No `created_at` / `updated_at` columns
for MVP — added later if/when needed.

The `lineup` table is intentionally **denormalized** (one row per team with
fixed slot columns) for MVP simplicity. A normalized `lineup_slot` child
table is deferred until variable formations or historical lineup snapshots
are needed.

- **season** — `id`, `seed` (int), `user_team_id` (fk team, nullable until picked),
  `current_matchday` (int), `status` (`active` | `complete`).
- **team** — `id`, `season_id`, `name`, `abbreviation` (3 chars).
- **skater** — `id`, `team_id`, `name`, `age`, `position` (`LW`|`C`|`RW`|`LD`|`RD`),
  `skating`, `shooting`, `passing`, `defense`, `physical` (all 0-100).
  Overall is derived (not stored) for MVP.
- **goalie** — `id`, `team_id`, `name`, `age`, `reflexes`, `positioning`,
  `rebound_control`, `puck_handling`, `mental` (0-100).
- **lineup** — one row per team. Slots:
  `line1_lw_id`, `line1_c_id`, `line1_rw_id`, ... `line4_*` (12 forward slots),
  `pair1_ld_id`, `pair1_rd_id`, `pair2_*`, `pair3_*` (6 D slots),
  `starting_goalie_id`, `backup_goalie_id`.
  Each slot is a fk to skater/goalie. Default lineup is auto-generated on
  league creation; user edits the user team's lineup.
- **game** — `id`, `season_id`, `matchday` (int), `home_team_id`, `away_team_id`,
  `status` (`scheduled` | `simulated`), `home_score`, `away_score`,
  `home_shots`, `away_shots`, `result_type` (`REG` | `OT` | `SO`, null until simulated),
  `seed` (int — derived per game).
- **game_event** — `id`, `game_id`, `tick` (int), `kind` (`shot` | `goal` | `save`),
  `team_id`, `primary_skater_id` (nullable), `assist1_id`, `assist2_id`,
  `goalie_id` (nullable). Stored append-only for box score reconstruction.

  Field conventions for all event kinds (`shot`, `save`, `goal`):
  - `team_id` = the **attacking / shooting** team.
  - `primary_skater_id` = the shooter (and, for `goal`, the scorer).
  - `goalie_id` = the **defending** goalie.
  - `assist1_id` / `assist2_id` are populated **only** for `goal` events;
    null for `shot` and `save`.
- **skater_game_stat** — `id`, `game_id`, `skater_id`, `goals`, `assists`,
  `shots`. Points derived.
- **goalie_game_stat** — `id`, `game_id`, `goalie_id`, `shots_against`, `saves`,
  `goals_against`. Save% derived.
- **standing** — one row per team per season. `team_id`, `season_id`, `games_played`,
  `wins`, `losses`, `ot_losses`, `points`, `goals_for`, `goals_against`.

Single-league MVP: `season` row count is always 0 or 1.

## 4. Simulation

### Contract

```python
@dataclass(frozen=True)
class SimSkater:
    id: int
    position: Position  # LW|C|RW|LD|RD
    skating: int; shooting: int; passing: int; defense: int; physical: int

@dataclass(frozen=True)
class SimGoalie:
    id: int
    reflexes: int; positioning: int; rebound_control: int
    puck_handling: int; mental: int

@dataclass(frozen=True)
class SimLine:
    skaters: tuple[SimSkater, ...]   # 3 forwards or 2 defensemen

@dataclass(frozen=True)
class SimTeamLineup:
    forward_lines: tuple[SimLine, SimLine, SimLine, SimLine]
    defense_pairs: tuple[SimLine, SimLine, SimLine]
    starting_goalie: SimGoalie

@dataclass(frozen=True)
class SimGameInput:
    home: SimTeamLineup
    away: SimTeamLineup
    seed: int

class ResultType(Enum):
    REG = "REG"; OT = "OT"; SO = "SO"

@dataclass(frozen=True)
class SimGameResult:
    home_score: int; away_score: int
    home_shots: int; away_shots: int
    result_type: ResultType
    events: tuple[SimEvent, ...]
    skater_stats: tuple[SimSkaterStat, ...]
    goalie_stats: tuple[SimGoalieStat, ...]

def simulate_game(input: SimGameInput) -> SimGameResult: ...
```

### Tick model

- 60 minutes of regulation = 60 ticks (one tick ≈ 60 seconds of game time).
- A precomputed deterministic on-ice schedule rotates lines:
  forwards 40/30/20/10% of ticks across L1–L4, D pairs 45/35/20% across P1–P3.
- Per tick:
  1. Roll possession winner (weighted by on-ice skating + passing aggregate).
  2. Roll shot/no-shot (weighted by attacker offense vs defender defense).
  3. If shot: pick shooter (weighted by shooting), roll save vs goalie
     (reflexes + positioning), maybe goal.
  4. If goal: 0–2 assists picked from on-ice attackers (weighted by passing).
  5. Append `game_event` records; increment per-skater/goalie tallies.

### Tie-breaking

If tied after 60 ticks: enter **OT phase** — sudden-death extra ticks, capped
at 5 ticks. First goal wins → `result_type = OT`. If still tied, **shootout**:
weighted coin flip using aggregate shooter vs goalie strength → `result_type = SO`.
The shootout winner is recorded as a 1-goal differential in stats.

### Determinism

Single `random.Random` seeded with `input.seed`. The per-game seed is derived
**deterministically** in the service before calling sim, using a stable
formula (not Python's built-in `hash()`, which is salted per-process):

```python
import hashlib
digest = hashlib.sha256(f"{season.seed}:{game.id}".encode()).digest()
game_seed = int.from_bytes(digest[:8], "big")
```

Same `(season.seed, game.id)` always yields the same `game_seed`, across
processes and Python versions. Same input → same result, byte-for-byte.

## 5. Services & API

### Services

- `create_league(seed)` — generate teams, players, default lineups, schedule,
  empty standings. Reset if one already exists.
- `set_user_team(team_id)`.
- `get_lineup(team_id)` / `set_lineup(team_id, lineup_dto)` — validates slot
  positions, no duplicates, all slots filled.
- `advance_matchday()` — owns the transaction:
  1. Open one outer transaction.
  2. Load all `scheduled` games for `current_matchday`.
  3. For each: load lineups, build `SimGameInput`, call `simulate_game`,
     persist `game`, `game_event`s, `skater_game_stat`s, `goalie_game_stat`s.
  4. Update `standing` rows (W/L/OTL, GF/GA, PTS).
  5. Increment `season.current_matchday`; mark `complete` if no more games.
  6. Commit once. Repos do not commit.

### Standings points

| result_type | winner | loser |
|-------------|--------|-------|
| REG         | +2     | +0    |
| OT / SO     | +2     | +1 (OTL) |

For MVP, the `standing.ot_losses` column counts **both OT losses and SO
losses** (no separate SOL column). This matches the points table — both
yield +1 to the loser — and avoids extra columns until a real need appears.

### API surface

```
GET    /api/health
POST   /api/league                  { seed }                creates/resets the single MVP league
GET    /api/league                                          season + user_team_id
PUT    /api/league/user-team        { team_id }
GET    /api/teams
GET    /api/teams/{id}
GET    /api/teams/{id}/roster
GET    /api/teams/{id}/lineup
PUT    /api/teams/{id}/lineup
GET    /api/schedule
GET    /api/standings
GET    /api/games/{id}                                      box score + events
POST   /api/season/advance                                  synchronous; returns advanced game IDs
GET    /api/season/status
```

`POST /api/league` accepts `{ seed }` **only**. It creates or resets the
single MVP league (any existing season + dependent rows are wiped) and
defaults `user_team_id` to the first generated team. The client typically
follows up with `PUT /api/league/user-team` once the user picks a team
from the team-picker UI.

### Domain errors

`LeagueNotFound` (404), `TeamNotFound` (404), `GameNotFound` (404),
`LineupInvalid` (422), `LineupSlotConflict` (422), `SeasonAlreadyComplete` (409).
Serialized as `{ error_code, message }`.

### Schedule generation

Round-robin: each pair plays `games_per_pairing` (MVP default = 3) → 9 matchdays
× 2 games = 18 total games. Configurable constant for future 82-game scaling.

## 6. Frontend

### Stack

React + Vite + TypeScript, **TanStack Router** (file-based), TanStack Query,
Tailwind CSS. No component library. Layout:

```
frontend/src/
  routes/                file-based routes
  components/            Card, Table, Button, StatBadge, TeamBadge
  api/                   fetch wrapper + generated types
  queries/               useXxx hooks (queries + mutations)
  lib/
  main.tsx
```

### Routes

```
/                        Dashboard
/team/$teamId            Team page (roster + summary)
/team/$teamId/lineup     Lineup editor (only enabled for user team)
/schedule                Full schedule + results
/standings               Standings table
/game/$gameId            Box score
/season-complete         End screen
```

### Query keys

`['league']`, `['teams']`, `['team', id]`, `['team', id, 'roster']`,
`['team', id, 'lineup']`, `['schedule']`, `['standings']`, `['game', id]`,
`['season', 'status']`.

### Mutation invalidations

- `PUT /api/teams/{id}/lineup` → invalidate `['team', id, 'lineup']`.
- `PUT /api/league/user-team` → invalidate `['league']`.
- `POST /api/season/advance` → invalidate `['schedule']`, `['standings']`,
  `['season','status']`, and any `['game', *]` (predicate). Response includes
  simulated game IDs for deep-linking.

### First-run flow

1. App boot → `GET /api/league`.
2. 404 → New League screen → `POST /api/league { seed }` (random default).
3. Response carries generated teams → team picker → `PUT /api/league/user-team`.
4. No client-side persistence beyond Query cache.

### Pages

- **Dashboard**: user team summary, next-game card, last-result card,
  top-4 standings snippet, prominent **Advance** button. Disabled when season
  complete (links to `/season-complete`).
- **Team page**: header (name, abbr, record), roster grouped by position with
  attributes. "Edit lineup" only for user team.
- **Lineup editor**: 4 forward lines, 3 D pairs, starting + backup goalie.
  Drag-or-select assignment from roster pool. Client-side validation mirrors
  backend rules; backend errors surface inline.
- **Schedule**: matchday-grouped; user games highlighted; completed games link
  to box score.
- **Standings**: GP / W / L / OTL / PTS / GF / GA / DIFF; user team highlighted.
- **Box score**: score + result_type badge (REG/OT/SO), shots, skater stats
  (G/A/PTS), goalie stats (SA/SV/SV%), event log.
- **Season complete**: champion (top of standings), final table, "New League"
  CTA → `POST /api/league` reset.

### Manager-perspective UX

- User's team highlighted in every table.
- Only the user team's lineup is editable.
- "Advance" is the single progression action; surfaced on dashboard and nav.

### Error UI

Central fetch wrapper maps `{ error_code, message }` → typed errors. Toasts
for `SeasonAlreadyComplete` and network errors; inline form errors for
`LineupInvalid` / `LineupSlotConflict`; full-page error for `LeagueNotFound`
(routes back to first-run flow).

### Out of scope (frontend)

Auth UI, multi-save UI, animations, charts, dark mode, mobile-first layouts.

## 7. Testing

Pytest, focused on simulation and standings:

- `simulate_game` is deterministic: same `(input, seed)` → identical result.
- Score totals match event log (goals events == final scores).
- Standings math: REG/OT/SO scenarios produce correct W/L/OTL/PTS.
- `advance_matchday` advances exactly the current matchday's games and bumps
  the pointer.
- Schedule generator produces the expected number of games and balanced pairings.

Frontend tests deferred unless a specific UI behavior becomes complex.

## 8. Phase Exit Criteria

- App runs locally via:
  - Postgres available locally (e.g. `brew install postgresql@16 && brew services start postgresql@16`) with database `hockey_manager` created (`createdb hockey_manager`). Tests share this DB and roll back via an outer transaction.
  - `cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload`
  - `cd frontend && npm install && npm run dev`
- User can create a league, pick a team, view roster, edit lineup, advance
  through every matchday, see updated standings and box scores, and reach the
  season-complete screen.
- Sim has determinism and standings tests passing.
