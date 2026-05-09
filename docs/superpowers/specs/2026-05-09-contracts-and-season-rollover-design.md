# Contracts + Season Rollover — Design (P1.3)

## Context

This is the foundation for the franchise-management features on the roadmap (Free Agency v2, Trades v2, Draft, Waivers). It introduces contracts as first-class entities and the season-rollover mechanism that turns the game from a single-season demo into a multi-season franchise sim.

Salary cap is **explicitly deferred**. Contracts here carry `salary` as a number with no enforcement — it feeds asset valuation and display only. Cap math (and buyouts, signing bonuses, etc.) lands in a later spec.

The end goal is a full contract lifecycle (negotiation, RFA/UFA, NTC/NMC, two-way, bonuses). This spec keeps the door open to all of it without building any of it speculatively. Each deferred field lands with the system that consumes it.

## Goals

- Every player on a team has a contract with `length`, `signed_season_year`, `expires_after_year`, `salary`, `no_trade_clause`.
- Contracts expire at season rollover; expired players become FAs automatically.
- The user signs FAs with chosen terms (length, salary, NTC).
- NTC blocks trades.
- A new `offseason` phase exists between playoffs and the next regular season.
- A "Start New Season" action atomically performs rollover (tick contracts, age players, create the next season).
- Player age becomes computed from `birth_date` + `season.year` — no per-row aging tick.

## Non-goals

See the deferred table at the end. Notably out of scope: salary cap, RFA/UFA, re-sign window, negotiation, NMC, two-way, retirement, AI signings, draft picks as assets.

---

## Data model

### New table: `contract`

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `skater_id` | int FK → `skater.id`, nullable | XOR with `goalie_id` |
| `goalie_id` | int FK → `goalie.id`, nullable | XOR with `skater_id` |
| `length` | int | Original deal length in years; immutable. |
| `signed_season_year` | int | `season.year` at signing. |
| `expires_after_year` | int | Last season covered. Initially `signed_season_year + length - 1`; stored (not computed) so future extensions can mutate it. |
| `salary` | int | Per-year base salary, integer in "thousands" for display (e.g. `8250` → "$8.25M"). Salaries are intentionally abstract: no cap consumes them yet, so the scale is tuned for NHL-like UI flavor and is free to change in the cap spec. |
| `no_trade_clause` | bool, default false | |
| `status` | enum: `active` \| `expired` \| `terminated` | Lifecycle state. Drives "is this player a FA" without depending on year math at query sites. |
| `terminated_season_year` | int, nullable | The `season.year` at which `status` flipped to `terminated` (release). Null otherwise. |
| `created_at` | timestamp | |

**Constraints:**
- CHECK: exactly one of `skater_id` / `goalie_id` is non-null.
- **Partial unique index** `WHERE status = 'active'` on `skater_id`, and a second on `goalie_id`. DB-enforced: a player can have at most one active contract. Postgres handles partial unique indexes on a constant predicate cleanly.
- Status transitions: `active → expired` (rollover, via `expires_after_year < new_year`); `active → terminated` (release). `expired` and `terminated` are terminal — historical contracts are immutable.

### Changes to `skater` / `goalie`

- **Add** `birth_date: Date NOT NULL`.
- **Drop** `age` column. Age is **computed at the service/API boundary** with an explicit `season.year` argument: `def age(player, season_year) -> int: return season_year - player.birth_date.year`. No global "current season" implicit lookup, no SQLAlchemy hybrid property — historical views (e.g. a player's age in season 2026 vs 2028) remain correct because the caller passes the relevant year.
- Migration backfills `birth_date` for existing rows: `year = current_season.year - old_age`, month and day random from a deterministic seed (so re-running the migration yields the same dates).

### Changes to `season`

- **Add** `year: int NOT NULL`. Existing rows backfill to `2025`.
- **Allowed `phase` values**: existing values plus new `"offseason"`. No schema change if `phase` is a free-form string column; otherwise update the enum.

### Status / phase semantics

To avoid confusion as `offseason` is introduced:

- `season.status` describes the **season container** lifecycle: `active` = this is the season we're operating on; `complete` = closed, archived (set when rollover creates the next season).
- `season.phase` describes **what's happening inside the active season**: `regular_season` (matchdays running), `playoffs` (bracket running), `offseason` (between playoffs and the next season's rollover).
- `phase = "offseason"` with `status = "active"` is the **expected** state between champion-crowning and Start-New-Season. It does *not* mean regular-season games are active.

### "Free agent" definition

Unchanged: `team_id IS NULL` ⇔ FA. Equivalently and more directly: a FA is a player with no contract whose `status = 'active'`. The two conditions are kept in sync by every code path that sets one (sign, release, rollover).

---

## Initial contract generation (league creation)

Runs once, in the same hook that seeds players, teams, and the FA pool. Deterministic from the league seed.

For each rostered skater and goalie:

1. **Length** drawn from weighted distribution: 1y=15%, 2y=30%, 3y=25%, 4y=20%, 5y=10%. Constants live in a single config module.
2. **`signed_season_year`** drawn uniformly from `[season.year - length + 1, season.year]` so a deal might be in any year of its term at league start. Yields stagger: ~1/length of contracts expire each future year.
3. **`expires_after_year`** = `signed_season_year + length - 1`.
4. **Salary** = `clamp(salary_floor + ovr_factor * (ovr - ovr_baseline), salary_min, salary_max)`. Initial constants: `salary_floor=750`, `ovr_baseline=60`, `ovr_factor=250`, `salary_min=750`, `salary_max=15000`. A 90 OVR earns ~8250 ("$8.25M"); a 60 OVR earns ~750 ("$0.75M", roughly a league-minimum analog); the cap headroom (~$15M) leaves room for star deals. Numbers are abstract units in "thousands"; no cap consumes them yet, so the scale is free to change when the cap spec lands.
5. **NTC** = `false`. NTC is granted in negotiations, which v1 doesn't model.

FA pool players get **no contract row**. Birth dates generated alongside players from the same league seed (`birth_year = league_start_year - target_age`, month and day random).

---

## Sign-FA flow

### Endpoint

`POST /api/teams/{team_id}/sign/{kind}/{player_id}` gains a Pydantic body:

```json
{
  "length": 2,
  "salary": 1500,
  "no_trade_clause": false
}
```

Validation:
- `length` ∈ [1, 8].
- `salary` ∈ [`salary_min`, `salary_max`].
- Player is currently a FA (`team_id IS NULL` and no contract with `status = 'active'`). Else 409.
- Caller owns the team (existing rule).

Behavior on success (one transaction):
1. Set `player.team_id = team_id`.
2. Insert a `contract` row with `signed_season_year = season.year`, `length`, `expires_after_year = season.year + length - 1`, `salary`, `no_trade_clause`.
3. Return updated player + contract.

### Frontend

`/free-agents`: existing "Sign" button opens a modal instead of acting directly.

Modal contents:
- Length picker (1–8, default 2).
- Salary number input, default = `suggested_salary(player.ovr)` using the same formula as initial generation.
- NTC checkbox (default unchecked).
- Sign / Cancel.

On success: close modal, invalidate FA list and roster queries.

No negotiation. Sign always succeeds if validation passes. The body shape is the natural extension point for accept/reject in the future.

---

## Trade integration

### NTC blocks trades

Before evaluating value, if either player has `no_trade_clause = true`, the trade is rejected with reason `"no-trade clause"`. No prompt, no override.

Trade-block computation also excludes NTC holders from candidate lists so the user doesn't see ghosts they can't acquire.

### Contract terms factor into value (light)

Augment the existing evaluator:

```
contract_modifier = (years_remaining - 2) * length_weight
                  - (salary - market_salary(ovr)) * salary_weight
```

Where:
- `years_remaining = expires_after_year - season.year + 1`.
- `market_salary(ovr)` reuses the initial-generation salary formula.
- `length_weight = 0.5`, `salary_weight = 0.001` (tunable, intentionally small in v1; cap-era will increase weights).

Net effect: long-term, under-market deals are mild assets; short-term, over-market deals are mild liabilities.

### Release behavior

Release **preserves history**. On release:

1. Set `player.team_id = NULL`.
2. Find the player's `active` contract; flip `status = 'terminated'`, set `terminated_season_year = season.year`.
3. Clear lineup slots referencing them (mirrors the existing flow).

No buyout cost (buyouts are a cap-era feature). Release modal copy: "Releasing this player ends their contract immediately. Contract history is kept for the record."

---

## Season rollover + offseason phase

### Phase transitions

```
regular_season → playoffs → offseason → (new season's regular_season)
```

The existing `_advance_playoffs` function in `backend/app/services/advance_service.py` currently sets `season.status = "complete"` when the final concludes. Change: set `season.phase = "offseason"` and keep `status = "active"`. `champion_team_id` continues to be set.

### Endpoint: `POST /api/season/rollover`

Preconditions: latest season has `phase = "offseason"`. Else 409.

Behavior (one transaction):

1. Mark current season `status = "complete"`.
2. Create new `Season` row: `year = old.year + 1`, `current_matchday = 1`, `phase = "regular_season"`, `status = "active"`, `seed` derived from `(old.seed, new.year)`.
3. **Tick contracts:** for every `active` contract where `expires_after_year < new_season.year`, flip `status = 'expired'`. The player now has no active contract — set `team_id = NULL` and clear lineup slots referencing them (mirrors release flow). Contract rows stay as history (status = `expired`).
4. **Aging** is implicit via the computed `age` property (`new_season.year - birth_date.year`). No per-row update.
5. Generate schedule for new season (existing schedule generator, new season + seed).
6. Create fresh `Standing` rows for every team for the new season.
7. Recompute trade-block for the new season (existing P1.2 hook).
8. FA pool: previously unsigned players stay; newly expired players join. All age via the year bump. No retirement logic.

### Idempotency

The `phase = "offseason"` precondition plus the immediate `status = "complete"` flip prevents double-rollover. A second call returns 409.

### Frontend

- The existing season-complete / champion screen gains a **"Start New Season"** button when `phase === "offseason"`. Clicking calls `POST /api/season/rollover` and routes to the dashboard.
- Dashboard handles `phase === "offseason"`: no games to advance; show "Offseason — start new season" with the same button.
- Optional informational list: "Expiring this offseason" (contracts where `expires_after_year === current_year`). Read-only.

---

## UI surfaces (summary)

| Surface | Change |
|---|---|
| Player rows everywhere | Small contract badge: `2y · $1.5M`, plus `NTC` tag if applicable |
| Player detail page | Contract section: length, signed year, expires year, salary, NTC |
| `/free-agents` | Sign button opens modal (length / salary / NTC) instead of one-click |
| Roster page | Columns or tooltip showing years remaining, salary, NTC |
| Release confirm modal | Copy: "Releasing this player ends their contract immediately. Contract history is kept for the record." |
| `/trade-block` | Show contract terms on each candidate; NTC holders excluded server-side |
| Trade rejection | Surface `"no-trade clause"` reason text |
| Season-complete / dashboard | "Start New Season" button when `phase === "offseason"` |
| Dashboard / header | `Year YYYY` indicator |

---

## Testing strategy

### Migration / model

- Backfill: every existing skater/goalie has non-null `birth_date`; `age(player, current_season.year)` matches old stored value at migration time.
- CHECK constraint: contract row with both or neither of `skater_id` / `goalie_id` rejected.
- Partial unique index: cannot insert two `active` contracts for the same player; *can* have multiple `expired` / `terminated` rows alongside one `active`.
- Status state machine: `active → expired` and `active → terminated` allowed; `expired`/`terminated` rows are not mutated by any code path.

### Generation (deterministic)

- Same league seed → identical contracts (length, salary, signed_year, NTC).
- Length distribution within tolerance over a full league.
- Every rostered player has exactly one active contract; FAs have none.
- Expiry years staggered (no single year holds >50%).

### Sign FA

- Valid body → new contract row; player on team; FA list excludes player.
- Length out of range → 422.
- Signing an already-signed player → 409.
- Authorization unchanged (user team only).

### Trades

- NTC holder excluded from trade-block.
- Trade involving NTC → rejected with reason `"no-trade clause"`.
- Contract modifier moves value as expected (longer / under-market = higher value).

### Rollover

- Phase transitions playoffs → offseason → regular_season (next year).
- `season.year` increments; `age(player, new_year)` increments by 1 for every player.
- Players with `expires_after_year < new_year`: contract flipped to `expired`, player becomes FA, lineup slots cleared.
- Players with remaining years stay rostered with correct `years_remaining`; their contract stays `active`.
- Released-this-season players: their `terminated` contract is untouched by rollover.
- Double-rollover blocked (409).
- Calling rollover before offseason blocked (409).
- New season has fresh schedule, standings, trade-block.
- Prior season's stats, games, and historical contract rows untouched.

### Integration

Full flow: create league → sim full season → reach offseason → rollover → advance one matchday in the new season.

---

## Out of scope (deferred)

| Deferred | Lands in |
|---|---|
| Salary cap, buyouts | Cap spec |
| Signing bonuses | Cap spec |
| RFA / UFA distinction, qualifying offers | Free Agency v2 spec |
| Re-sign window (extend current player before expiry) | Free Agency v2 spec |
| Player accept/reject negotiation logic | Free Agency v2 spec |
| Two-way contracts | Minor-league spec |
| NMC (no-movement clause) | Waivers spec |
| AI signings, AI re-signs | Free Agency v2 spec |
| Retirement | Player Lifecycle spec |
| Trade deadline window | Trades v2 spec |
| Draft picks as contract assets | Draft spec |
| Per-player contract history page | Future polish |
| Mid-season contract extensions | Future polish |

Each deferred field/system has a target home; nothing is rejected, only sequenced.
