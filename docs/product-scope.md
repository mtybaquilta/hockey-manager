# Product Scope

## Current Phase

Phase 1: **Tiny Playable League**

The goal is to build a small, playable hockey management/simulation prototype before adding advanced franchise systems.

## Core Loop

```txt
View team → Set lineup → Simulate next game/day → Inspect result/stats → Advance
```

Every feature should support this loop.

## First Playable Milestone

The first milestone is:

```txt
4-team mini-season
```

The user should be able to play through a short season from start to finish.

## In Scope

### League

- One league
- 4 fictional teams
- Short regular season
- Basic season completion condition
- Optional simple final/championship game after the regular season

### Teams

- Team name
- Team abbreviation
- Team roster
- Basic team strength derived from player ratings

### Players

- Around 20 fictional players per team
- Name
- Age
- Position
- Overall rating
- Basic attributes, for example:
  - skating
  - shooting
  - passing
  - defense
  - physical
  - goalie rating, for goalies only

### Lineups

- Basic lineup view
- Basic lineup editing
- Enough validation to prevent obviously invalid lineups
- No advanced chemistry or tactical roles yet
- Per-team Gameplan (`style` + `line_usage`) is implemented in the sim and influences shots, goals, penalties, and line TOI. PP/PK units are auto-selected from the lineup. See `docs/phase-2.md`.

### Schedule

- Basic schedule generation or seeded fixture list
- Games have:
  - home team
  - away team
  - scheduled date/order
  - status

### Match Simulation

- Deterministic simulation using a seed
- Uses basic team/player strength
- Produces:
  - final score
  - shots
  - goal events
  - basic player stats
  - goalie stats if practical
- Same input and seed should produce the same result

### Standings

Track basic standings:

- games played
- wins
- losses
- overtime/shootout losses only if implemented simply
- points
- goals for
- goals against

### Free Agents (P1.1)

- Seeded pool of unsigned skaters and goalies generated at league creation.
- `/free-agents` page with filter by position/min OVR/min potential/max age and sort.
- The user team can sign free agents and release rostered players. Sign is instant; release confirms via modal.
- Released players return to the pool. Lineup slots referencing them are cleared automatically; stats are preserved.
- Implementation: `team_id` is nullable on `skater` and `goalie`; `team_id IS NULL` ⇔ free agent.

### Trades (P1.5)

- `/trades` page: offer builder with 1–3 players per side, AI partner selector, real-time evaluation outlook, and submit.
- `POST /api/trades/evaluate` and `POST /api/trades/execute`. Execute re-evaluates inside the transaction and only mutates if accepted.
- Per-player value formula: `ovr + age_modifier + position_need + potential_modifier + contender_modifier + round(contract_modifier)`.
- Acceptance: `offered_sum ≥ requested_sum + package_penalty` AND `best_offered ≥ best_requested − 5`. Package penalty = `max(0, len(offered) − len(requested)) × 3`.
- Structured rejection reasons: `ValueTooLow`, `NoTradeClause`, `PositionNeedMismatch`, `TopProspect`, `RosterFloor` (catastrophic only: skaters < 12 or goalies < 1).
- Non-blocking warnings: `RosterBelowActiveFloor` (skaters < 18 or goalies < 2 on either side), `LineupSlotsCleared`. Lineup gaps are gated by Advance, not by the trade itself.
- On accept: swap `team_id` for all involved players and clear referencing lineup slots on both teams in one transaction.
- Out of scope: salary cap, draft picks, retained salary, multi-team trades, trade deadline, AI-initiated trades, negotiation rounds.

### Contracts + Season Rollover (P1.3)

- Every rostered skater and goalie has exactly one active `contract` row at any time. Contracts carry `length`, `signed_season_year`, `expires_after_year`, `salary` (in $1k units, 750–15000), `no_trade_clause`, and `status` (`active` / `expired` / `terminated`).
- League creation generates one initial active contract per rostered player; free agents have no contract.
- Player age is computed from `birth_date` against `Season.year` (no `age` column).
- Free-agent signing requires terms (length 1–8, salary 750–15000, optional NTC). Release flips the active contract to `terminated` (history preserved) and the player becomes a free agent.
- Trade block excludes NTC holders; proposing a trade with either side carrying NTC returns `409 NoTradeClause`. Trade value adds a small contract modifier `(years_remaining - 2) * 0.5 - (salary - market) * 0.001`.
- When the Stanley Cup final ends, season transitions to `phase=offseason` (status stays `active`). Dashboard shows the offseason banner and a "Start New Season" button. Advancing during offseason is blocked.
- Rollover requires `phase=offseason`: ages players via the new `Season.year`, expires every active contract whose `expires_after_year < new_year`, frees those players (clears lineup slots, sets `team_id=null`), and refills empty lineup slots with the best available roster player by position.
- UI: roster + free-agents pages render a `ContractBadge` (`{years}y · ${salary}M` with optional NTC chip); player detail shows the same; trade block shows it on each candidate; sign-FA modal collects length/salary/NTC.

### UI

Minimum useful screens:

- Dashboard/home
- Teams list
- Team roster
- Lineup screen
- Schedule/results
- Game detail/box score
- Standings
- Season complete screen

### Tests

Add tests for:

- deterministic match simulation
- standings calculations
- schedule progression if implemented
- basic domain rules

## Out of Scope

Do not implement these during the first playable milestone unless explicitly requested:

- Trades
- Draft
- Salary cap
- Complex contracts
- Waivers
- Free agency (P1.1 implemented — basic FA pool + sign/release; deeper systems still deferred)
- Scouting
- Staff
- Player morale
- Line chemistry
- Advanced tactics (basic Gameplan style/line_usage is implemented; "advanced" here means matchup tactics, situational systems, etc.)
- Training systems
- Long-term player development
- Injuries
- News feed
- Media system
- Sponsorships
- Arena finances
- Multiplayer
- Real NHL teams, players, logos, jerseys, or protected IP
- Real-money monetization
- Complex live match visualization
- Real-time action gameplay
- Multi-league or international competitions

Put good deferred ideas into `docs/not-now.md`.

## Phase Exit Criteria

Phase 1 is complete when:

- The app can be run locally.
- A user can view the 4-team league.
- A user can inspect rosters.
- A user can view and adjust a basic lineup.
- A user can simulate games.
- Results update standings and stats.
- A user can advance through the whole mini-season.
- The season reaches a completed state.
- Core simulation logic has tests.
