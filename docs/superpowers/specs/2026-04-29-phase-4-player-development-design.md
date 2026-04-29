# Phase 4 — Player Development & Multi-Season Progression

## Goal

Let the user complete a season, start the next season, and see players age, improve, and decline. The 4-team mini-season becomes a multi-season save with visible career arcs, while keeping the project's "smallest useful version" discipline.

## Scope

- Add `potential` and `development_type` to skaters and goalies.
- Generate `potential` and `development_type` during league creation.
- Add deterministic end-of-season player development.
- Age all players by +1 during season rollover.
- Keep same teams and rosters across seasons.
- Generate a new schedule and reset standings on rollover.
- Preserve old games, stats, events, and standings for career/history.
- Add a persisted development summary surfaced via API.
- Add development history and career totals to player detail endpoints.

## Non-Goals

- Draft, trades, free agency, contracts, salary cap, retirements, scouting tiers, player morale, multi-save/auth, multi-league. These remain in `docs/not-now.md`.
- Per-attribute potentials (single overall ceiling only).
- Denormalized per-season aggregate tables (computed on read for now).

## Hard Rules

- Development must be deterministic from the new season's seed and player identity.
- Attribute values stay in `[20, 100]`.
- Current overall remains derived from attributes; not stored.
- `potential` is a soft ceiling; rare overshoot is allowed.
- Pure simulation (`backend/sim/development.py`) must not import FastAPI or SQLAlchemy.
- `decline` lowers attributes only; never lowers `potential`.

## Architecture

Two new layers, mirroring the existing `sim/engine.py` ↔ `services/advance_service.py` split:

- **`backend/sim/development.py`** — pure, deterministic. Functions take dataclasses in, return dataclasses out. Owns the formula: age curve × potential gap × development_type modifier × performance signal → per-attribute deltas + summary reason.
- **`backend/app/services/season_rollover_service.py`** — orchestrates rollover: validates current season, computes league averages and per-player perf signals from last season's `*_game_stat`, builds sim inputs, calls `develop_player`, persists `season_progression` + `development_event`, applies new attributes, ages players +1, creates next `Season`, generates schedule via existing schedule generator, creates fresh standings rows. Single transaction.

## Data Model

### Column additions

- `skater.potential` int (0–100), NOT NULL.
- `skater.development_type` varchar(16), NOT NULL. Allowed: `steady`, `early_bloomer`, `late_bloomer`, `boom_or_bust`.
- `goalie.potential` int (0–100), NOT NULL.
- `goalie.development_type` varchar(16), NOT NULL.
- `game.season_id` FK → `season.id`, NOT NULL.
- `standing.season_id` FK → `season.id`, NOT NULL. Unique `(season_id, team_id)`.

Backfill in migration:
- For existing players: `potential = clamp(overall + small_random(0..6), 0, 100)`, `development_type = 'steady'`.
- For existing games and standings: set `season_id` to the current active season's id.

### New tables

**`season_progression`** — one row per player per rollover.

| column | type | notes |
| --- | --- | --- |
| id | int PK | |
| from_season_id | int FK season.id | the just-completed season |
| to_season_id | int FK season.id | the new season |
| player_type | varchar(8) | `skater` or `goalie` |
| player_id | int | plain int; resolved via `player_type` |
| age_before | int | |
| age_after | int | always `age_before + 1` |
| overall_before | int | derived overall before development |
| overall_after | int | derived overall after development |
| potential | int | snapshot at time of rollover |
| development_type | varchar(16) | snapshot at time of rollover |
| summary_reason | varchar(16) | `growth`, `decline`, `boom`, `bust`, `plateau`, `mixed` |

Indexes: `(to_season_id)`, `(player_type, player_id)`.

**`development_event`** — one row per changed attribute.

| column | type | notes |
| --- | --- | --- |
| id | int PK | |
| season_progression_id | int FK season_progression.id | cascade delete |
| attribute | varchar(32) | e.g. `skating`, `reflexes` |
| old_value | int | |
| new_value | int | |
| delta | int | signed |
| reason | varchar(16) | `growth`, `decline`, `boom`, `bust` |

Index: `(season_progression_id)`.

If a player has no attribute changes, write a `season_progression` row with `summary_reason = plateau` and zero `development_event` rows.

## Development Formula

Pure function:

```python
def develop_player(
    player: PlayerDevInput,        # id, type, age, attrs, potential, development_type, perf_signal
    season_seed: int,
) -> PlayerDevResult                # new_attrs, events, summary_reason, overall_before, overall_after
```

Determinism: `rng = Random(hash((season_seed, player_type, player_id)))`. Performance signal is precomputed by the orchestrator and passed in, so the pure function has no DB dependency.

### Per-attribute step

1. **Direction probability** from age curve. Each age bucket maps to `(p_grow, p_decline)`; remainder is `p_stable`. Initial values (to be tuned in tests):

   Skaters:
   | age | p_grow | p_decline |
   | --- | --- | --- |
   | 18–22 | 0.55 | 0.00 |
   | 23–26 | 0.30 | 0.02 |
   | 27–31 | 0.10 | 0.05 |
   | 32–34 | 0.03 | 0.25 |
   | 35+ | 0.01 | 0.45 |

   Goalies (shifted +2 years per the agreed buckets):
   | age | p_grow | p_decline |
   | --- | --- | --- |
   | 18–24 | 0.55 | 0.00 |
   | 25–28 | 0.30 | 0.02 |
   | 29–33 | 0.10 | 0.05 |
   | 34–36 | 0.03 | 0.25 |
   | 37+ | 0.01 | 0.45 |

2. **Development type modifier:**
   - `steady` ×1.0 across the curve.
   - `early_bloomer`: `p_grow ×1.3` for ages 18–23; `p_grow ×0.6` for ages ≥27. Earlier plateau.
   - `late_bloomer`: `p_grow ×0.6` for ages 18–23; `p_grow ×1.3` for ages 24–29. Later plateau.
   - `boom_or_bust`: probability scaling ×1.0 base, but variance scale 2.0× (see step 5).

3. **Potential gap modifier:** `gap = potential - overall_before`. `p_grow *= clamp(0.2 + gap/15, 0.2, 1.5)`. If `gap <= 0`, `p_grow *= 0.15` (soft cap; rare overshoot still possible).

4. **Performance modifier (small):** `s ∈ [-1, 1]`. `p_grow *= (1 + 0.15 * s)`, `p_decline *= (1 - 0.15 * s)`. DNP / very-low GP: `s = 0`.

5. **Roll & magnitude:** `r = rng.random()`.
   - If `r < p_grow` → growth, magnitude `1 + (1 if rng.random() < 0.25 else 0)`. For `boom_or_bust`: magnitude 2 chance is 50%, plus 5% chance of magnitude 3.
   - Elif `r > 1 - p_decline` → decline, magnitude 1. For `boom_or_bust`: magnitude 2 chance is 30%.
   - Else stable.

6. **Clamp** new attribute value to `[20, 100]`.

### Summary reason

Computed in this order (first match wins):

1. No events → `plateau`.
2. All events grow AND at least one delta magnitude ≥ 2 AND `development_type == boom_or_bust` → `boom`.
3. All events decline AND at least one delta magnitude ≥ 2 AND `development_type == boom_or_bust` → `bust`.
4. Mixed signs (both growth and decline events present) → `mixed`.
5. Net positive sum of deltas → `growth`.
6. Net negative sum of deltas → `decline`.
7. Otherwise → `plateau`.

The UI may present `summary_reason` plus the actual overall change separately.

### Performance signal (orchestrator-side)

Computed before calling the pure function so `sim/development.py` stays DB-free.

- **Skater:** `s = clamp(((player_pts_per_gp / league_avg_pts_per_gp) - 1) * gp_weight, -1, 1)` where `gp_weight = min(gp / 20, 1)`.
- **Goalie:** `s = clamp(((player_sv_pct - league_avg_sv_pct) / 0.020) * gp_weight, -1, 1)` where `gp_weight = min(gp / 10, 1)`.

If league average denominator is zero (no games), `s = 0` for everyone.

## Rollover Flow

`POST /api/season/start-next` → `season_rollover_service.start_next_season(db)`:

1. Load current active `Season`. If none → 404 `NoActiveSeason`. If `status != 'completed'` → 409 `SeasonNotComplete`. If any `game.status != 'completed'` for that season → 409 `SeasonNotComplete`.
2. Compute league averages from completed season's `skater_game_stat` / `goalie_game_stat`, filtered by `game.season_id = current.id`.
3. Compute per-player perf signals for every skater and goalie (DNP → `s=0`).
4. Derive `new_seed = (current.seed * 31 + current.id) & 0x7FFFFFFF`.
5. For each player: build `PlayerDevInput`, call `develop_player(...)`, collect result.
6. In a single transaction:
   - Insert new `Season(seed=new_seed, user_team_id=current.user_team_id, current_matchday=1, status='active')`.
   - For each player: insert `season_progression`, insert `development_event` rows for changed attributes, update player attribute columns, increment `age` by 1.
   - Generate schedule for new season via existing schedule generator (scoped to `new_season.id`).
   - Insert fresh `standing` rows (one per team, `season_id = new_season.id`, zeroed).
7. Return `{ new_season, development_summary }`.

Idempotency: not enforced via dedup key. The 409 guard plus the prior season's `status = 'completed'` flip prevents double-rollover under normal flow.

## API Surface

- **POST `/api/season/start-next`** — body: none. `200 { new_season, development_summary }` | `404 NoActiveSeason` | `409 SeasonNotComplete`.
- **GET `/api/season/development-summary?season_id=X`** — `season_id` is the `to_season_id` of the rollover; defaults to most recent rollover if omitted. Returns:
  ```json
  {
    "season_id": 2,
    "progressions": [
      {
        "player_type": "skater",
        "player_id": 17,
        "player_name": "...",
        "team_id": 3,
        "age_before": 24, "age_after": 25,
        "overall_before": 78, "overall_after": 80,
        "potential": 86,
        "development_type": "late_bloomer",
        "summary_reason": "growth",
        "events": [
          { "attribute": "skating", "old_value": 80, "new_value": 82, "delta": 2, "reason": "growth" }
        ]
      }
    ]
  }
  ```
- **GET `/api/players/{id}/development?type=skater|goalie`** — `200 { player, history: [<season_progression with events, ordered by to_season_id desc>] }`. 404 if player not found.
- **GET `/api/players/{id}/career?type=skater|goalie`** — `200 { player, by_season: [...], totals: {...} }`. Skater fields: `gp, g, a, pts, plus_minus, sog`. Goalie fields: `gp, w, l, sv_pct, gaa, shutouts`. Computed by grouping `*_game_stat` joined to `game` on `season_id`.

Pydantic schemas: `app/schemas/development.py`, `app/schemas/career.py`.

## League Generation

Existing player generation extended to set:

- `potential`: drawn deterministically from the league seed. Base bump by age:
  - age ≤ 22: `bump = randint(6, 16)`
  - age 23–26: `bump = randint(2, 8)`
  - age 27–30: `bump = randint(0, 4)`
  - age ≥ 31: `bump = 0` (already at or near peak)
  - Then `potential = clamp(overall + bump, overall, 100)`. 5% of rows get `bump = 0` regardless of age (already-peaked players). 5% of rows under age 25 get `bump += randint(3, 6)` (high-ceiling outliers).
- `development_type`: `steady` 50%, `early_bloomer` 20%, `late_bloomer` 20%, `boom_or_bust` 10%. Deterministic from league seed.

## UI

Initial UI work, scoped tightly to enable the loop:

- Season-complete screen exposes a "Start Next Season" action that calls `POST /api/season/start-next` and routes to a development summary view.
- Development summary view groups progressions by team (or by largest overall change) with the `78 → 80` and per-attribute deltas visible.
- Player detail page gains a "Development" tab (history) and a "Career" tab (per-season + totals). `potential` displayed as `OVR / POT` (e.g., `76 OVR / 84 POT`).

UI polish (sorting, filtering, label mapping of numeric potential to scout-style tiers) is deferred.

## Testing

Pure-sim tests (`backend/tests/test_development.py`):

- **Determinism**: same input + seed → identical events list (run twice, deep-equal).
- **Young high-potential**: cohort at age 19, `potential=90, overall=70`, many seeds → mean Δoverall > 0; growth events frequent.
- **Older decline**: cohort at age 35 → mean Δoverall < 0; growth events rare.
- **Soft cap**: `overall ≥ potential` → growth probability sharply reduced, not zero (rare overshoot).
- **Dev type shape**: `early_bloomer` outgrows `late_bloomer` at age 20 and is outgrown at age 27. `boom_or_bust` variance > `steady` variance at same age/potential.
- **Performance modifier**: above-avg perf increases growth probability; DNP signal is neutral.
- **Summary reason ordering**: mixed-sign events → `mixed` even when net positive.

Service / integration tests (`backend/tests/test_season_rollover.py`):

- **Guards**: active (uncompleted) season → 409; completed season with leftover non-completed games → 409.
- **Schedule + standings reset**: new season has fresh schedule and zeroed standings; no leftover scheduled games from prior season.
- **History preserved**: old games, stats, events, standings, and progressions are still queryable after rollover.
- **Aging**: every player's `age` is +1 after rollover.
- **Career endpoint**: spans ≥ 2 seasons; per-season totals match raw stat sums; totals = sum of by_season.
- **Development summary persistence**: rows returned by `GET /api/season/development-summary` exactly match what `POST /api/season/start-next` returned.

## Migration

Single Alembic migration:

1. Add `potential`, `development_type` columns to `skater` and `goalie` (nullable initially).
2. Backfill: `potential = clamp(overall + random(0..6), 0, 100)`, `development_type = 'steady'`. Then set NOT NULL.
3. Add `season_id` to `game` and `standing` (nullable initially).
4. Backfill: set to current active season's id.
5. Set NOT NULL, add FKs and `(season_id, team_id)` unique on `standing`.
6. Create `season_progression` and `development_event` tables.

## Out of Scope (Deferred)

Already in `docs/not-now.md`. Reaffirmed for this phase: no draft, trades, free agency, contracts, salary cap, retirements, scouting tiers, injuries, player morale, multi-save/auth.
