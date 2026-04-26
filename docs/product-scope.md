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
- Free agency
- Scouting
- Staff
- Player morale
- Line chemistry
- Advanced tactics
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
