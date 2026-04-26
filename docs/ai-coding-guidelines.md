# AI Coding Guidelines

## Purpose

These guidelines are for AI coding agents working on this project.

The main goal is to keep the project small, playable, and maintainable.

## General Rules

- Keep changes small and scoped.
- Work within `docs/product-scope.md`.
- Do not silently add features outside the current phase.
- Do not introduce new frameworks, services, or architectural patterns without explicit approval.
- Prefer simple, readable code over clever abstractions.
- Build vertical slices that produce visible, playable progress.
- Avoid broad unfinished layers.

## Required Behavior

Before coding:

1. Read `CLAUDE.md`.
2. Read `docs/agent-context.md`.
3. Read `docs/product-scope.md`.
4. Read this file.
5. Check `docs/not-now.md` for deferred ideas.

When given a task:

1. Restate the intended scope briefly.
2. Identify which files or areas are likely to change.
3. Keep implementation limited to the task.
4. Add or update tests where appropriate.
5. Do not add unrelated cleanup or refactors unless requested.

## Scope Control

If a feature is outside current scope:

- Do not implement it.
- Add it to `docs/not-now.md` if it is a useful future idea.
- Continue with the smallest useful current-scope implementation.

Examples of scope creep:

- Adding trades while implementing rosters.
- Adding contracts while implementing players.
- Adding injuries while implementing match simulation.
- Adding scouting while implementing player ratings.
- Adding Redis/Celery while implementing simple background jobs.

## Simulation Rules

Simulation code must be pure and testable.

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

Simulation code should not depend on:

- FastAPI
- SQLAlchemy sessions
- HTTP requests
- environment variables
- current wall-clock time
- external services

Simulation should receive all required input explicitly.

## Determinism

Simulation must be deterministic when given the same input and seed.

Example:

```python
result_1 = simulate_game(input, seed=123)
result_2 = simulate_game(input, seed=123)

assert result_1 == result_2
```

Avoid hidden randomness.

Use an explicit random generator seeded inside the simulation.

## Backend Guidelines

Use:

- FastAPI for API routes
- Pydantic for request/response schemas
- SQLAlchemy for database models and persistence
- Alembic for migrations

Rules:

- Keep route handlers thin.
- Put application workflows in service modules.
- Put database queries in repositories or clearly separated persistence functions.
- Do not put complex business logic directly inside route handlers.
- If schema changes, add an Alembic migration.
- If adding endpoints, add Pydantic schemas.

Suggested layering:

```txt
api route
  → service/workflow
    → repository/database access
    → simulation function if needed
```

## Frontend Guidelines

Use:

- React
- Vite
- TypeScript
- TanStack Query for server state
- Tailwind CSS for styling
- React Router or TanStack Router for routing

Rules:

- Use TanStack Query for data fetched from the backend.
- Use local React state for component-only UI state.
- Do not add Zustand unless client-only UI state becomes painful across multiple components.
- Keep components small and focused.
- Prefer feature folders when a screen grows.

Do not store server data in client-only global state unless there is a strong reason.

## Testing Guidelines

Prioritize tests for:

- simulation determinism
- match results
- standings calculations
- schedule progression
- domain rules

Use pytest for backend/simulation tests.

Frontend tests can come later unless a UI behavior is complex.

## Database Guidelines

Early domain entities should stay simple.

Likely early models:

- League
- Season
- Team
- Player
- Game
- GameEvent
- Standing
- Lineup

Avoid adding these until explicitly needed:

- Contract
- Trade
- DraftPick
- Injury
- Scout
- StaffMember
- NewsItem
- SalaryCapRecord

## Background Job Guidelines

Start simple.

Initial simulation may run directly inside FastAPI requests if it is fast.

Later options:

- Postgres-backed jobs table
- Supabase Queues / pgmq
- Separate Python worker process

Do not add:

- Redis
- RabbitMQ
- Celery
- SQS
- Lambdas
- Temporal

unless explicitly requested.

## IP and Content Rules

Do not use real NHL teams, player names, logos, jerseys, trademarks, or protected IP.

Use fictional teams and fictional players unless the user explicitly provides legally cleared data.

## Code Style

- Use type hints in Python.
- Use TypeScript types on the frontend.
- Prefer explicit names over abbreviations.
- Keep functions small.
- Avoid premature abstraction.
- Avoid magic numbers in simulation logic when a named constant would help.
- Add comments only where they explain non-obvious domain logic.

## Default Principle

When uncertain, implement the smallest version that supports the current playable loop.
