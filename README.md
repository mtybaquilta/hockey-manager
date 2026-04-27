# Hockey Manager (MVP)

A small web-based hockey management/simulation game. Phase 1 is a 4-team mini-season MVP that proves the core loop:

```
View team → Set lineup → Simulate next game/day → Inspect result/stats → Advance
```

## Run locally

Prereqs: macOS with Postgres available locally (e.g. Postgres.app or `brew install postgresql@16`), `uv` for Python, Node 20+.

```bash
# 1. Postgres
createdb hockey_manager           # one-time

# 2. Backend (from repo root)
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload         # http://localhost:8000

# 3. Frontend (in another shell)
cd frontend
npm install
npm run dev                                  # http://localhost:5173
```

Open http://localhost:5173 in a browser. You'll be prompted to create a league with a seed; afterwards you can advance the season matchday by matchday.

## Test

```bash
cd backend && uv run pytest
cd frontend && npx tsc --noEmit
```

## Layout

- `backend/app/` — FastAPI routes, services, repositories, SQLAlchemy models, Pydantic schemas.
- `backend/sim/` — pure deterministic game simulation. No FastAPI/SQLAlchemy/web dependency.
- `backend/data/` — fictional team and player name pools.
- `backend/alembic/` — DB migrations.
- `frontend/src/` — React app (TanStack Router/Query, Tailwind).
- `docs/` — product scope, agent context, AI guidelines, design spec, implementation plan.
