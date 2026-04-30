# Phase 5A — Basic Gameplan / Tactics

## Goal

Give the user meaningful between-game decisions without adding trades, contracts, injuries, scouting, or complex tactics. Each team has a small `gameplan` (style + line usage) that nudges the deterministic simulation. The user edits their team's gameplan; AI teams have deterministic personalities visible to the user.

## Scope

- New `team_gameplan` row per team: `style`, `line_usage`.
- User team's gameplan is editable; AI gameplans are read-only and visible.
- Gameplan flows into the pure simulation as a new dataclass; modifies shot probability, shot-quality tilt, defensive suppression, penalty probability, and line selection.
- AI gameplans deterministically generated at league creation from the league seed.
- Gameplans persist across season rollover.
- Frontend: `Gameplan` card on each team page; user team's card is editable.

## Non-Goals

- Injuries, fatigue, trades, contracts, draft, scouting, special-teams lineup editor, complex player roles, line matching. Already in `docs/not-now.md`.
- Direct effects on goalie save probability. Quality-tilt and shot-suppression do all the work.
- AI gameplans changing during the season or at rollover.

## Hard Rules

- Determinism: same `SimGameInput` + seed → identical `SimGameResult`.
- Pure sim (`backend/sim/`) must not import SQLAlchemy models or Pydantic schemas.
- Gameplan is per-team identity; rollover does not modify it.
- Shot-quality weights must remain non-negative and positive-sum after gameplan shifts.
- Defensive suppression is applied exactly once per shot.

## Architecture

Two layers, mirroring existing patterns:

- **Pure sim:** Adds `SimGameplan` and `SimTeamInput` dataclasses to `sim/models.py`. `SimGameInput.home/away` become `SimTeamInput` (lineup + gameplan). New `sim/constants.py` holds all numeric modifiers. `sim/engine.py` reads constants when computing shot probability, shot-quality weights, defensive suppression, and penalty probability. New pure helper `sim/rotation.py::build_rotation_schedule(total_ticks, distribution)` precomputes which line/pair plays each tick.
- **Service / API:** `app/services/gameplan_service.py` validates and persists. `advance_service.py` loads `team_gameplan` alongside `Lineup` and builds `SimTeamInput`. Errors `GameplanInvalid` (422) and `NotUserTeam` (403). Pydantic schemas in `app/schemas/gameplan.py`.

## Data Model

### New table `team_gameplan`

| column | type | notes |
| --- | --- | --- |
| id | int PK | |
| team_id | int FK `team.id` ON DELETE CASCADE, UNIQUE | one row per team |
| style | varchar(16) NOT NULL | CHECK in (`balanced`, `offensive`, `defensive`, `physical`) |
| line_usage | varchar(16) NOT NULL | CHECK in (`balanced`, `ride_top_lines`, `roll_all_lines`) |

Allowed values are enforced by:
- DB CHECK constraints,
- service-layer validation in `gameplan_service.py`,
- Pydantic `Literal` types on the API schemas.

### Insertion points

- `create_or_reset_league` (after teams are generated): insert one `team_gameplan` per team. User team gets `(balanced, balanced)`. AI teams sampled deterministically from the league seed using:
  - `style`: 50% balanced / 20% offensive / 20% defensive / 10% physical.
  - `line_usage`: 60% balanced / 25% ride_top_lines / 15% roll_all_lines.
- Season rollover: untouched.
- `set_user_team`: gameplans untouched. The newly selected user team simply becomes editable.

### Migration

Single Alembic migration:
1. Create `team_gameplan` with columns above and CHECK constraints on `style` / `line_usage`.
2. Backfill: insert one row per existing team using `(balanced, balanced)`.

## Sim Integration

### `sim/constants.py`

```python
GAMEPLAN_STYLE_MODIFIERS = {
    "balanced":  {"shot_prob": 1.00, "opp_shot_prob": 1.00, "def_suppression": 1.00,
                  "shot_quality_self": 0.00, "shot_quality_opp": 0.00,
                  "self_penalty": 1.00, "opp_penalty": 1.00},
    "offensive": {"shot_prob": 1.06, "opp_shot_prob": 1.00, "def_suppression": 0.97,
                  "shot_quality_self": +0.05, "shot_quality_opp": 0.00,
                  "self_penalty": 1.00, "opp_penalty": 1.00},
    "defensive": {"shot_prob": 0.95, "opp_shot_prob": 0.95, "def_suppression": 1.00,
                  "shot_quality_self": 0.00, "shot_quality_opp": -0.05,
                  "self_penalty": 1.00, "opp_penalty": 1.00},
    "physical":  {"shot_prob": 1.00, "opp_shot_prob": 1.00, "def_suppression": 0.97,
                  "shot_quality_self": 0.00, "shot_quality_opp": -0.05,
                  "self_penalty": 1.35, "opp_penalty": 1.10},
}

LINE_USAGE_FORWARD_DISTRIBUTION = {
    "balanced":       (0.40, 0.30, 0.20, 0.10),
    "ride_top_lines": (0.48, 0.32, 0.15, 0.05),
    "roll_all_lines": (0.30, 0.27, 0.23, 0.20),
}
LINE_USAGE_DEFENSE_DISTRIBUTION = {
    "balanced":       (0.45, 0.35, 0.20),
    "ride_top_lines": (0.52, 0.35, 0.13),
    "roll_all_lines": (0.38, 0.34, 0.28),
}
```

### Dataclasses (`sim/models.py`)

```python
@dataclass(frozen=True)
class SimGameplan:
    style: Literal["balanced", "offensive", "defensive", "physical"]
    line_usage: Literal["balanced", "ride_top_lines", "roll_all_lines"]

@dataclass(frozen=True)
class SimTeamInput:
    lineup: SimTeamLineup
    gameplan: SimGameplan
```

`SimGameInput.home` / `away` become `SimTeamInput`. Existing tests that build `SimGameInput` directly with `SimTeamLineup` are updated to wrap in `SimTeamInput(..., gameplan=SimGameplan("balanced", "balanced"))`.

### Engine changes (`sim/engine.py`)

1. **Shot probability** in `_attempt_shot`:
   - `shot_prob = base_shot_prob × attacker.gameplan.style.shot_prob × defender.gameplan.style.opp_shot_prob`.
   - The `defender_def` value passed in is multiplied **once**, upstream in `_on_ice_attackers_and_def`, by `defender.gameplan.style.def_suppression`. No second multiplication anywhere.
2. **Shot-quality weights** in `_classify_shot_quality`:
   - After computing existing margin- and strength-based weights, add `attacker.shot_quality_self - defender.shot_quality_opp` to `HIGH` and subtract the same from `LOW` (preserving total weight). After the shift, clamp each weight to `≥ 0.02`. If total drops to `0`, restore `_BASE_QUALITY_WEIGHTS`.
3. **Penalty probability** in `_maybe_penalty`:
   - `effective = PENALTY_PER_TICK_PROB × (attacker.self_penalty + defender.opp_penalty) / 2`.
   - Penalty assignment (which side takes it) still uses each on-ice skater's `physical` weight; the gameplan only changes total frequency.
4. **Line selection**:
   - Replace tick-based `forward_line_at_tick` / `defense_pair_at_tick` calls with lookups into precomputed schedules.
   - Build per-team rotation schedules once at the start of `simulate_game` using `build_rotation_schedule(REGULATION_TICKS, dist)` and (for OT) `build_rotation_schedule(OT_MAX_TICKS, dist)`. The OT schedule simply continues using the regular-time distribution.

### `sim/rotation.py::build_rotation_schedule`

Pure function. Signature:

```python
def build_rotation_schedule(total_ticks: int, distribution: tuple[float, ...]) -> tuple[int, ...]:
```

Behavior:
- Compute exact target counts: `counts[i] = round(total_ticks * distribution[i])`. Adjust the largest bucket so `sum(counts) == total_ticks`.
- Distribute (not cluster) line indices across the schedule using a Bresenham-style stride so any short window approximates the target distribution. Deterministic from inputs (no rng).
- Return tuple of length `total_ticks` of line indices.

Tested independently for: target counts, deterministic output, no clustering (max-run-length bound for any index).

## Service Layer

### `app/services/gameplan_service.py`

```python
ALLOWED_STYLES = {"balanced", "offensive", "defensive", "physical"}
ALLOWED_LINE_USAGES = {"balanced", "ride_top_lines", "roll_all_lines"}

def get_team_gameplan(db, team_id) -> TeamGameplan        # raises TeamNotFound
def update_user_team_gameplan(db, team_id, style, line_usage) -> TeamGameplan
    # raises TeamNotFound, NotUserTeam, GameplanInvalid

def generate_gameplans_for_league(rng, db, team_ids, user_team_id) -> None
    # idempotent: deletes existing rows first, then inserts one row per team
```

`generate_gameplans_for_league` is called from `league_service.create_or_reset_league` after teams are generated.

### Errors

Add to `app/errors.py`:

```python
class GameplanInvalid(DomainError):
    code = "GameplanInvalid"
    status = 422

class NotUserTeam(DomainError):
    code = "NotUserTeam"
    status = 403
```

## API

- `GET /api/teams/{team_id}/gameplan` → `200 GameplanOut { team_id, style, line_usage, editable }`. 404 `TeamNotFound`.
- `PUT /api/teams/{team_id}/gameplan` body `{ style, line_usage }` → `200 GameplanOut`. 404 `TeamNotFound` | 403 `NotUserTeam` | 422 `GameplanInvalid`.

`editable` is `true` iff `team_id == current_season.user_team_id`.

## Frontend

- **Types** (`frontend/src/api/types.ts`): `Gameplan`, plus literal unions matching backend.
- **Queries** (`frontend/src/queries/gameplan.ts`): `useTeamGameplan(teamId)`, `useUpdateTeamGameplan(teamId)`. Mutation invalidates `["team-gameplan", teamId]`, `["schedule"]`, `["standings"]`.
- **Team detail page** (`team.$teamId.tsx`): add `Gameplan` card below the roster. For non-user teams, two read-only chips. For the user team, two `<select>` controls + Save button (disabled while pending).
- Tooltip on the user-team card: "Gameplan applies to future-simulated games, not games already played."

## Testing

### Pure-sim tests (`backend/tests/test_gameplan_sim.py`)

1. **Determinism:** same `SimGameInput` + seed → equal `SimGameResult`. Run twice for `(offensive, ride_top_lines)` and `(balanced, balanced)`.
2. **Offensive ↑ shots-for:** N=200 sims, identical lineups, varying seeds; team A `offensive` vs team A `balanced`. `mean(shots_for_A | offensive) > mean(shots_for_A | balanced)`.
3. **Defensive ↓ shots-against:** N=200; team A `defensive` vs `balanced`. Lower opponent shots when defensive.
4. **Physical ↑ penalties:** N=200; both teams `physical` vs both `balanced`. More PENALTY events when physical.
5. **`ride_top_lines` ↑ top-line involvement:** count line-1 forward shot attempts; higher than `balanced`. Line-4 lower.
6. **`roll_all_lines` flattens:** line-1 lower than `balanced`; line-4 higher.
7. **Player quality dominates:** strong team (avg attrs +10) `defensive` vs weak team (avg attrs −10) `offensive`. N=100. Strong team's mean goal differential remains positive.
8. **Shot-quality weights remain valid:** call `_classify_shot_quality` repeatedly with `offensive` and `defensive` shifts; assert no weight ever goes below 0.02.
9. **`build_rotation_schedule` correctness:** `(180, (0.40, 0.30, 0.20, 0.10))` → counts exactly `(72, 54, 36, 18)`. Max-run-length per index ≤ small bound (e.g., `≤ 4`). Deterministic across calls.

### Service / API tests (`backend/tests/test_gameplan_api.py`)

- `GET /api/teams/{user_team_id}/gameplan` returns `editable=true`. Non-user team returns `editable=false`.
- `PUT` on user team with valid values → 200, persisted.
- `PUT` on non-user team → 403 `NotUserTeam`.
- `PUT` with invalid `style` or `line_usage` → 422 `GameplanInvalid`.
- `PUT` with non-existent team → 404 `TeamNotFound`.
- After `create_or_reset_league`: every team has a gameplan; user team is `(balanced, balanced)`.
- After `season_rollover_service.start_next_season`: every team's gameplan equals its pre-rollover values.
- After `set_user_team`: gameplans of all teams unchanged; previous user team remains read-only-eligible (no longer editable from the new user team's perspective).

## Out of Scope (Deferred)

Reaffirmed in `docs/not-now.md`: injuries, fatigue, trades, contracts, draft, scouting, special-teams lineup editor, complex player roles, line matching, special-teams gameplan controls.
