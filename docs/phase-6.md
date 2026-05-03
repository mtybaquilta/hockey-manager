# Phase 6 — Roster Agency

## P1.1 Free Agent Pool (implemented)

Seeded pool at league creation, FA listing endpoints, and sign/release gated to the user team.

See `docs/superpowers/specs/2026-05-03-free-agent-pool-design.md` for the full design and `docs/superpowers/plans/2026-05-03-free-agent-pool.md` for the implementation plan.

### Data model

- `skater.team_id` and `goalie.team_id` are nullable; `team_id IS NULL` ⇔ free agent. FK is `ON DELETE SET NULL`.
- All skater/goalie FKs on `lineup` are nullable so release can clear referenced slots.

### Endpoints

- `GET /api/free-agents/skaters` — filters: `position`, `min_ovr`, `min_potential`, `max_age`; sort: `ovr|potential|age|position`.
- `GET /api/free-agents/goalies` — filters and sort minus `position`.
- `POST /api/teams/{team_id}/sign/{skater|goalie}/{player_id}` — user team only.
- `POST /api/teams/{team_id}/release/{skater|goalie}/{player_id}` — user team only; auto-clears lineup slots.

### Out of scope (P1.1)

AI signings, roster size limits, transfer windows, role/archetype attributes, contracts, salary cap, trades, draft, scouting.
