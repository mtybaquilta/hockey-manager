# CLAUDE.md

## Project

This is a web-based hockey management/simulation game.

It is **not** an action game. The focus is team management, roster decisions, lineup choices, match simulation, standings, stats, and season progression.

## Required Reading

Before making changes, read:

- `docs/agent-context.md`
- `docs/product-scope.md`
- `docs/ai-coding-guidelines.md`
- `docs/not-now.md` if it exists

Follow these files unless the user explicitly overrides them.

## Current Priority

Build the first playable milestone:

```txt
4-team mini-season
```

The game should support the core loop:

```txt
View team → Set lineup → Simulate next game/day → Inspect result/stats → Advance
```

Do not add advanced systems until this mini-season is playable from start to finish.

## Tech Stack

Frontend:

- React
- Vite
- TypeScript
- TanStack Query
- React Router or TanStack Router
- Tailwind CSS

Backend:

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL / Supabase Postgres

Simulation:

- Pure Python
- Deterministic
- Seed-based
- Tested with pytest
- No FastAPI or database dependency inside pure simulation functions

Background jobs:

- Start simple
- Use direct FastAPI execution first where acceptable
- Later use Postgres-backed jobs or Supabase Queues/pgmq
- Do not add Redis, RabbitMQ, Celery, SQS, Lambdas, or other job infrastructure unless explicitly requested

## Non-Negotiable Rules

- Keep changes small and scoped.
- Do not add features outside `docs/product-scope.md`.
- Do not introduce new frameworks or services without approval.
- Keep simulation logic separate from FastAPI and SQLAlchemy.
- Add tests for simulation behavior.
- If changing schema, add an Alembic migration.
- If adding API endpoints, use Pydantic request/response schemas.
- Do not use real NHL teams, players, logos, or protected IP.
- Prefer vertical slices over broad unfinished layers.
- When uncertain, implement the smallest useful version.

## Default Response to Scope Creep

If a requested feature is not needed for the current playable loop, add it to `docs/not-now.md` instead of implementing it.
