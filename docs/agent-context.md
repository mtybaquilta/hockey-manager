# Agent Context

## Project Summary

We are building a web-based hockey management/simulation game inspired by the simulation and franchise-management side of games like NHL/FHM/Football Manager.

This is **not** an action hockey game. There is no real-time playable 3D/2D match control. The focus is on managing a team, simulating games and seasons, and making roster/lineup/strategy decisions.

The project should eventually support systems like rosters, lineups, match simulation, standings, player stats, player development, injuries, trades, contracts, drafts, AI managers, and news. However, the project must start with a very small playable version.

The immediate goal is to build a **4-team mini-season MVP** that proves the core loop.

## Current Product Goal

Build a playable mini-season where the user can:

1. Pick or view a team.
2. View roster and player ratings.
3. View schedule.
4. Set or inspect a basic lineup.
5. Simulate games.
6. See results, box scores, and standings.
7. Advance through a short season.
8. Reach a season complete screen.

The first milestone is successful when a user can play through a full short season from start to finish.

## Core Gameplay Loop

```txt
View team → Set lineup → Simulate next game/day → Inspect result/stats → Advance
```

Every feature should support this loop. Features that do not support this loop should be deferred.

## Tech Stack

### Frontend

- React
- Vite
- TypeScript
- TanStack Query
- React Router or TanStack Router
- Tailwind CSS

Optional later:

- Zustand for complex client-only UI state

### Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL, likely Supabase Postgres

### Platform

Supabase may be used for:

- Postgres
- Auth
- Storage
- Realtime
- Queues / pgmq

Avoid using Edge Functions for heavy simulation work.

### Simulation

- Pure Python simulation engine
- Deterministic seed-based logic
- No FastAPI dependency
- No database dependency inside pure simulation functions
- Heavily tested with pytest

## Architecture Principles

### Keep Simulation Pure

Simulation code should be callable without a web server or database.

Good:

```python
def simulate_game(input: GameSimulationInput, seed: int) -> GameSimulationResult:
    ...
```

Bad:

```python
def simulate_game(request: Request, db: Session):
    ...
```

The API or worker should load data from the database, convert it into simulation input, call the pure simulation function, then persist the result.

### Keep API Thin

FastAPI route handlers should mostly:

1. Validate input.
2. Call a service/workflow.
3. Return a response.

Complex game logic should not live directly in route handlers.

### Keep Persistence Separate

SQLAlchemy code should not leak into pure simulation logic.

Use repositories or clearly separated persistence functions to load and save database state.

## Suggested Project Structure

```txt
apps/
  web/                  # React/Vite frontend

backend/
  app/
    api/                # FastAPI routes
    services/           # application workflows
    repositories/       # SQLAlchemy database access
    models/             # SQLAlchemy models
    schemas/            # Pydantic schemas
    workers/            # future job worker code

  sim/
    engine.py           # pure simulation logic
    models.py           # simulation-only dataclasses/types
    ratings.py
    standings.py
    schedule.py

  tests/
    test_sim_engine.py
    test_standings.py
```

The exact folder structure can evolve, but the boundary between API/database code and simulation code should remain clear.

## Preferred Implementation Style

Use vertical slices instead of building huge layers.

Good sequence:

1. Create teams in database.
2. Show teams in UI.
3. Create players.
4. Show roster.
5. Create schedule.
6. Show next game.
7. Simulate one game.
8. Show result.
9. Update standings.
10. Complete mini-season.

Avoid building all models, all APIs, all screens, or all simulation systems upfront.

## Determinism Requirement

Simulation should be deterministic when given the same input and seed.

This is important for:

- Testing
- Debugging
- Replays
- Balancing
- Save-game integrity

Example expectation:

```python
result_1 = simulate_game(input, seed=123)
result_2 = simulate_game(input, seed=123)

assert result_1 == result_2
```

## Save-Game Integrity

Game progression should avoid corrupting saves.

Important rules:

- Avoid partially completed world advancement.
- Prefer explicit status fields such as `scheduled`, `simulated`, `completed`.
- Make simulation actions retry-safe where possible.
- Store enough result data to reconstruct game summaries.
- Keep game events or box score data instead of only final scores.

## Initial Domain Concepts

Likely early entities:

- League
- Season
- Team
- Player
- Game
- GameEvent
- Standing
- Lineup

Avoid adding advanced entities too early.

Deferred entities:

- Contract
- Trade
- DraftPick
- Injury
- Scout
- StaffMember
- NewsItem
- SalaryCapRecord

## First Playable Milestone

The first milestone is:

```txt
4-team mini-season
```

Suggested rules:

- 4 fictional teams
- 20 fictional players per team
- Each team plays a short schedule
- Top team or top two teams produce a champion/final
- Basic standings are tracked
- Games produce scores and simple player stats
- User can advance until the season is complete

This milestone should be prioritized over all advanced features.

## Design Philosophy

The project should grow from a small working game, not from a huge unfinished simulation design.

The correct default answer to new features is:

```txt
Not now. Add it to docs/not-now.md.
```

Add complexity only when the current playable loop needs it.
