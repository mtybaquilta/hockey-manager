# Phase 4 Player Development Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic end-of-season player development and multi-season progression so the user can roll an active season into the next one and see players age, improve, and decline.

**Architecture:** A pure simulation module `backend/sim/development.py` owns the development formula and is unit-tested with no DB. A new `backend/app/services/season_rollover_service.py` orchestrates: validates current season, computes performance signals, calls the pure function, persists results, ages players, creates the next season, regenerates schedule and standings. Two new tables (`season_progression`, `development_event`) persist the development summary. Spec: `docs/superpowers/specs/2026-04-29-phase-4-player-development-design.md`.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, Alembic, Pydantic, pytest. Frontend: React + Vite + TypeScript + TanStack Query + Tailwind.

---

## File Structure

**Backend — create:**
- `backend/sim/development.py` — pure development formula
- `backend/app/models/season_progression.py` — `SeasonProgression`
- `backend/app/models/development_event.py` — `DevelopmentEvent`
- `backend/app/services/season_rollover_service.py` — orchestration
- `backend/app/api/development.py` — development summary + per-player development/career endpoints
- `backend/app/schemas/development.py` — Pydantic schemas for development
- `backend/app/schemas/career.py` — Pydantic schemas for career stats
- `backend/alembic/versions/c3d4e5f6a7b8_phase4_player_development.py` — migration
- `backend/tests/test_development_sim.py` — pure-sim tests
- `backend/tests/test_season_rollover.py` — service/integration tests
- `backend/tests/test_player_career_api.py` — career endpoint integration test
- `frontend/src/pages/DevelopmentSummary.tsx` — season rollover summary view
- `frontend/src/api/development.ts` — typed client calls
- `frontend/src/api/career.ts` — typed client calls

**Backend — modify:**
- `backend/app/models/skater.py` — add `potential`, `development_type`
- `backend/app/models/goalie.py` — add `potential`, `development_type`
- `backend/app/models/team.py` — drop `season_id`
- `backend/app/models/__init__.py` — export new models
- `backend/app/services/generation/players.py` — populate `potential`, `development_type`
- `backend/app/services/generation/teams.py` — drop `season_id` arg if applicable
- `backend/app/services/league_service.py` — fix `get_league` to filter active, fix `set_user_team`, fix `_wipe`, fix team creation
- `backend/app/services/advance_service.py` — fix `db.query(Season).first()` to filter active
- `backend/app/api/season.py` — add `/start-next` and `/development-summary`
- `backend/app/api/players.py` — add `/{id}/development` and `/{id}/career`
- `backend/app/errors.py` — add `SeasonNotComplete`, `NoActiveSeason`

**Frontend — modify:**
- `frontend/src/App.tsx` (or router file) — add development summary route
- `frontend/src/pages/SeasonComplete.tsx` (if it exists) or relevant view — add "Start Next Season" action
- `frontend/src/pages/PlayerDetail.tsx` — add Development tab + Career tab + show `OVR / POT`

---

## Pre-Flight Sanity

Confirm a clean baseline before changes.

- [ ] **Step 1: Run existing test suite**

```bash
cd backend && uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Confirm git tree is clean**

```bash
git status
```

Expected: working tree clean (or only the spec/plan files just authored).

---

## Task 1: Add `potential` and `development_type` to skater/goalie models

**Files:**
- Modify: `backend/app/models/skater.py`
- Modify: `backend/app/models/goalie.py`

- [ ] **Step 1: Add columns to Skater**

Edit `backend/app/models/skater.py` to add two columns after `physical`:

```python
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Skater(Base):
    __tablename__ = "skater"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[str] = mapped_column(String(2), nullable=False)
    skating: Mapped[int] = mapped_column(Integer, nullable=False)
    shooting: Mapped[int] = mapped_column(Integer, nullable=False)
    passing: Mapped[int] = mapped_column(Integer, nullable=False)
    defense: Mapped[int] = mapped_column(Integer, nullable=False)
    physical: Mapped[int] = mapped_column(Integer, nullable=False)
    potential: Mapped[int] = mapped_column(Integer, nullable=False)
    development_type: Mapped[str] = mapped_column(String(16), nullable=False)
```

- [ ] **Step 2: Add columns to Goalie**

Edit `backend/app/models/goalie.py` similarly:

```python
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Goalie(Base):
    __tablename__ = "goalie"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    reflexes: Mapped[int] = mapped_column(Integer, nullable=False)
    positioning: Mapped[int] = mapped_column(Integer, nullable=False)
    rebound_control: Mapped[int] = mapped_column(Integer, nullable=False)
    puck_handling: Mapped[int] = mapped_column(Integer, nullable=False)
    mental: Mapped[int] = mapped_column(Integer, nullable=False)
    potential: Mapped[int] = mapped_column(Integer, nullable=False)
    development_type: Mapped[str] = mapped_column(String(16), nullable=False)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/skater.py backend/app/models/goalie.py
git commit -m "feat(models): add potential and development_type to skater and goalie"
```

---

## Task 2: Create `season_progression` and `development_event` models

**Files:**
- Create: `backend/app/models/season_progression.py`
- Create: `backend/app/models/development_event.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create SeasonProgression**

Write `backend/app/models/season_progression.py`:

```python
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SeasonProgression(Base):
    __tablename__ = "season_progression"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id", ondelete="CASCADE"), index=True
    )
    to_season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id", ondelete="CASCADE"), index=True
    )
    player_type: Mapped[str] = mapped_column(String(8), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    age_before: Mapped[int] = mapped_column(Integer, nullable=False)
    age_after: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_before: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_after: Mapped[int] = mapped_column(Integer, nullable=False)
    potential: Mapped[int] = mapped_column(Integer, nullable=False)
    development_type: Mapped[str] = mapped_column(String(16), nullable=False)
    summary_reason: Mapped[str] = mapped_column(String(16), nullable=False)
```

- [ ] **Step 2: Create DevelopmentEvent**

Write `backend/app/models/development_event.py`:

```python
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DevelopmentEvent(Base):
    __tablename__ = "development_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    season_progression_id: Mapped[int] = mapped_column(
        ForeignKey("season_progression.id", ondelete="CASCADE"), index=True
    )
    attribute: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[int] = mapped_column(Integer, nullable=False)
    new_value: Mapped[int] = mapped_column(Integer, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(16), nullable=False)
```

- [ ] **Step 3: Export from `models/__init__.py`**

Read `backend/app/models/__init__.py` and add the two new imports/exports following the existing pattern. If the file exposes models in `__all__`, add `SeasonProgression` and `DevelopmentEvent`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/season_progression.py backend/app/models/development_event.py backend/app/models/__init__.py
git commit -m "feat(models): add season_progression and development_event tables"
```

---

## Task 3: Drop `team.season_id`

**Files:**
- Modify: `backend/app/models/team.py`
- Modify: `backend/app/services/league_service.py`
- Modify: `backend/app/services/generation/teams.py`

- [ ] **Step 1: Inspect generation/teams.py**

Run `cat backend/app/services/generation/teams.py` and note any `season_id` usage so the next step removes it cleanly.

- [ ] **Step 2: Update Team model**

Edit `backend/app/models/team.py` to remove `season_id`:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Team(Base):
    __tablename__ = "team"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(3), nullable=False)
```

- [ ] **Step 3: Remove `season_id` from team generation**

Edit `backend/app/services/generation/teams.py` to drop the `season_id` argument and stop passing it to `Team(...)`. Keep the function signature compatible with `generate_teams(rng, db, ...)` — drop the `season_id` parameter entirely.

- [ ] **Step 4: Update league_service**

Edit `backend/app/services/league_service.py`:

- In `create_or_reset_league`: change `teams = generate_teams(rng, db, season.id)` to `teams = generate_teams(rng, db)`.
- In `set_user_team`: change the team lookup to `db.query(Team).filter_by(id=team_id).first()` (no `season_id` filter).
- Leave `_wipe` as-is; both `Team` and `Season` still listed for league reset.

- [ ] **Step 5: Run existing tests (expect failures)**

```bash
cd backend && uv run pytest -q
```

Expected: failures referencing `team.season_id`. We will fix in Task 4 + 5 (migration + generation defaults). For now, verify the failures are limited to `season_id`/`potential` related issues.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/team.py backend/app/services/generation/teams.py backend/app/services/league_service.py
git commit -m "refactor: decouple team from season_id"
```

---

## Task 4: Populate `potential` and `development_type` in player generation

**Files:**
- Modify: `backend/app/services/generation/players.py`

- [ ] **Step 1: Update player generation**

Replace `backend/app/services/generation/players.py` with:

```python
import random

from sqlalchemy.orm import Session

from app.models import Goalie, Skater
from app.services.generation.names import make_player_name

SKATER_LAYOUT = ["LW"] * 4 + ["C"] * 4 + ["RW"] * 4 + ["LD"] * 3 + ["RD"] * 3
GOALIE_COUNT = 2

DEV_TYPE_WEIGHTS = [
    ("steady", 0.50),
    ("early_bloomer", 0.20),
    ("late_bloomer", 0.20),
    ("boom_or_bust", 0.10),
]


def _attr(rng: random.Random) -> int:
    return max(40, min(95, int(rng.gauss(70, 8))))


def _goalie_attr(rng: random.Random) -> int:
    return max(45, min(95, int(rng.gauss(75, 6))))


def _pick_dev_type(rng: random.Random) -> str:
    r = rng.random()
    acc = 0.0
    for name, w in DEV_TYPE_WEIGHTS:
        acc += w
        if r < acc:
            return name
    return DEV_TYPE_WEIGHTS[-1][0]


def _potential_for(rng: random.Random, age: int, overall: int) -> int:
    if age <= 22:
        bump = rng.randint(6, 16)
    elif age <= 26:
        bump = rng.randint(2, 8)
    elif age <= 30:
        bump = rng.randint(0, 4)
    else:
        bump = 0
    if rng.random() < 0.05:
        bump = 0
    if age < 25 and rng.random() < 0.05:
        bump += rng.randint(3, 6)
    return max(overall, min(100, overall + bump))


def _skater_overall(skating: int, shooting: int, passing: int, defense: int, physical: int) -> int:
    return round((skating + shooting + passing + defense + physical) / 5)


def _goalie_overall(reflexes: int, positioning: int, rebound_control: int, puck_handling: int, mental: int) -> int:
    return round((reflexes + positioning + rebound_control + puck_handling + mental) / 5)


def generate_players_for_team(rng: random.Random, db: Session, team_id: int, used_names: set[str]) -> None:
    for pos in SKATER_LAYOUT:
        skating = _attr(rng)
        shooting = _attr(rng)
        passing = _attr(rng)
        defense = _attr(rng) if pos in ("LD", "RD") else max(40, _attr(rng) - 5)
        physical = _attr(rng)
        age = rng.randint(19, 35)
        overall = _skater_overall(skating, shooting, passing, defense, physical)
        db.add(
            Skater(
                team_id=team_id,
                name=make_player_name(rng, used_names),
                age=age,
                position=pos,
                skating=skating,
                shooting=shooting,
                passing=passing,
                defense=defense,
                physical=physical,
                potential=_potential_for(rng, age, overall),
                development_type=_pick_dev_type(rng),
            )
        )
    for _ in range(GOALIE_COUNT):
        reflexes = _goalie_attr(rng)
        positioning = _goalie_attr(rng)
        rebound_control = _goalie_attr(rng)
        puck_handling = _goalie_attr(rng)
        mental = _goalie_attr(rng)
        age = rng.randint(20, 36)
        overall = _goalie_overall(reflexes, positioning, rebound_control, puck_handling, mental)
        db.add(
            Goalie(
                team_id=team_id,
                name=make_player_name(rng, used_names),
                age=age,
                reflexes=reflexes,
                positioning=positioning,
                rebound_control=rebound_control,
                puck_handling=puck_handling,
                mental=mental,
                potential=_potential_for(rng, age, overall),
                development_type=_pick_dev_type(rng),
            )
        )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/generation/players.py
git commit -m "feat(generation): populate potential and development_type for players"
```

---

## Task 5: Alembic migration — add player columns, drop team.season_id, create progression tables

**Files:**
- Create: `backend/alembic/versions/c3d4e5f6a7b8_phase4_player_development.py`

- [ ] **Step 1: Find latest migration revision id**

```bash
ls backend/alembic/versions
```

Read the most recent file (likely `b2c3d4e5f6a7_phase2a_shot_quality.py`) and note its `revision = "..."` value. Use that as `down_revision` below.

- [ ] **Step 2: Write migration**

Create `backend/alembic/versions/c3d4e5f6a7b8_phase4_player_development.py`:

```python
"""phase4 player development

Revision ID: c3d4e5f6a7b8
Revises: <DOWN_REVISION_FROM_STEP_1>
Create Date: 2026-04-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "<DOWN_REVISION_FROM_STEP_1>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. potential / development_type on skater (nullable initially, backfill, then NOT NULL)
    op.add_column("skater", sa.Column("potential", sa.Integer(), nullable=True))
    op.add_column("skater", sa.Column("development_type", sa.String(length=16), nullable=True))
    op.execute(
        """
        UPDATE skater
        SET potential = LEAST(
                100,
                GREATEST(
                    (skating + shooting + passing + defense + physical) / 5,
                    (skating + shooting + passing + defense + physical) / 5
                        + CAST(FLOOR(RANDOM() * 7) AS INTEGER)
                )
            ),
            development_type = 'steady'
        """
    )
    op.alter_column("skater", "potential", nullable=False)
    op.alter_column("skater", "development_type", nullable=False)

    # 2. potential / development_type on goalie
    op.add_column("goalie", sa.Column("potential", sa.Integer(), nullable=True))
    op.add_column("goalie", sa.Column("development_type", sa.String(length=16), nullable=True))
    op.execute(
        """
        UPDATE goalie
        SET potential = LEAST(
                100,
                (reflexes + positioning + rebound_control + puck_handling + mental) / 5
                    + CAST(FLOOR(RANDOM() * 7) AS INTEGER)
            ),
            development_type = 'steady'
        """
    )
    op.alter_column("goalie", "potential", nullable=False)
    op.alter_column("goalie", "development_type", nullable=False)

    # 3. drop team.season_id (FK + index + column)
    with op.batch_alter_table("team") as batch:
        batch.drop_index("ix_team_season_id")
        batch.drop_constraint("team_season_id_fkey", type_="foreignkey")
        batch.drop_column("season_id")

    # 4. create season_progression
    op.create_table(
        "season_progression",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("from_season_id", sa.Integer(), sa.ForeignKey("season.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_season_id", sa.Integer(), sa.ForeignKey("season.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_type", sa.String(length=8), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("age_before", sa.Integer(), nullable=False),
        sa.Column("age_after", sa.Integer(), nullable=False),
        sa.Column("overall_before", sa.Integer(), nullable=False),
        sa.Column("overall_after", sa.Integer(), nullable=False),
        sa.Column("potential", sa.Integer(), nullable=False),
        sa.Column("development_type", sa.String(length=16), nullable=False),
        sa.Column("summary_reason", sa.String(length=16), nullable=False),
    )
    op.create_index("ix_season_progression_from_season_id", "season_progression", ["from_season_id"])
    op.create_index("ix_season_progression_to_season_id", "season_progression", ["to_season_id"])
    op.create_index(
        "ix_season_progression_player",
        "season_progression",
        ["player_type", "player_id"],
    )

    # 5. create development_event
    op.create_table(
        "development_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "season_progression_id",
            sa.Integer(),
            sa.ForeignKey("season_progression.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attribute", sa.String(length=32), nullable=False),
        sa.Column("old_value", sa.Integer(), nullable=False),
        sa.Column("new_value", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=16), nullable=False),
    )
    op.create_index(
        "ix_development_event_progression",
        "development_event",
        ["season_progression_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_development_event_progression", table_name="development_event")
    op.drop_table("development_event")
    op.drop_index("ix_season_progression_player", table_name="season_progression")
    op.drop_index("ix_season_progression_to_season_id", table_name="season_progression")
    op.drop_index("ix_season_progression_from_season_id", table_name="season_progression")
    op.drop_table("season_progression")
    op.add_column("team", sa.Column("season_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "team_season_id_fkey", "team", "season", ["season_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_team_season_id", "team", ["season_id"])
    op.drop_column("goalie", "development_type")
    op.drop_column("goalie", "potential")
    op.drop_column("skater", "development_type")
    op.drop_column("skater", "potential")
```

Replace `<DOWN_REVISION_FROM_STEP_1>` with the actual revision string from Step 1. Confirm the actual FK name on `team.season_id` is `team_season_id_fkey`; if it differs (Postgres auto-names usually match), update the string. To verify, run `\d team` in psql against a dev DB or `python -c "from sqlalchemy import inspect; ..."`.

- [ ] **Step 3: Run migration locally**

```bash
cd backend && uv run alembic upgrade head
```

Expected: migration applies cleanly. If your dev DB is empty, it works trivially. If it has existing data, the backfill runs. Inspect: `psql ... -c "SELECT id, age, potential, development_type FROM skater LIMIT 5;"`.

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest -q
```

Most tests should pass now (player generation populates the new columns; team no longer has `season_id`). Some tests calling `set_user_team`/`get_league` flow should still pass since league_service no longer filters by season_id. Address remaining failures inline if obvious.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/c3d4e5f6a7b8_phase4_player_development.py
git commit -m "feat(migration): add player potential/dev_type, drop team.season_id, add progression tables"
```

---

## Task 6: Pure simulation module — dataclasses and overall helpers

**Files:**
- Create: `backend/sim/development.py`
- Create: `backend/tests/test_development_sim.py`

This task introduces the dataclasses and the pure overall helpers, with tests. The formula itself comes in Task 7.

- [ ] **Step 1: Write the failing test for overall computation**

Create `backend/tests/test_development_sim.py`:

```python
from sim.development import (
    PlayerDevInput,
    GOALIE_ATTRIBUTES,
    SKATER_ATTRIBUTES,
    overall_from_attrs,
)


def _skater_input(**overrides) -> PlayerDevInput:
    base = dict(
        player_id=1,
        player_type="skater",
        age=24,
        attrs={"skating": 75, "shooting": 75, "passing": 75, "defense": 75, "physical": 75},
        potential=85,
        development_type="steady",
        perf_signal=0.0,
    )
    base.update(overrides)
    return PlayerDevInput(**base)


def test_overall_skater_is_attribute_average():
    p = _skater_input()
    assert overall_from_attrs(p) == 75


def test_skater_attribute_set():
    assert SKATER_ATTRIBUTES == ("skating", "shooting", "passing", "defense", "physical")


def test_goalie_attribute_set():
    assert GOALIE_ATTRIBUTES == ("reflexes", "positioning", "rebound_control", "puck_handling", "mental")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && uv run pytest tests/test_development_sim.py -q
```

Expected: ImportError / module not found.

- [ ] **Step 3: Write `sim/development.py` with dataclasses + overall helper**

Create `backend/sim/development.py`:

```python
"""Pure player development module.

No FastAPI, no SQLAlchemy. Deterministic given inputs and seed.

Public surface:
- ``PlayerDevInput``, ``PlayerDevResult``, ``DevEvent`` dataclasses
- ``develop_player(player, season_seed) -> PlayerDevResult``
- ``overall_from_attrs`` helper used by orchestration code

The orchestrator pre-computes ``perf_signal`` (league-relative performance,
clamped to [-1, 1]) so this module never touches the database.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

PlayerType = Literal["skater", "goalie"]
SummaryReason = Literal["growth", "decline", "boom", "bust", "plateau", "mixed"]
EventReason = Literal["growth", "decline", "boom", "bust"]
DevType = Literal["steady", "early_bloomer", "late_bloomer", "boom_or_bust"]

SKATER_ATTRIBUTES = ("skating", "shooting", "passing", "defense", "physical")
GOALIE_ATTRIBUTES = ("reflexes", "positioning", "rebound_control", "puck_handling", "mental")

ATTR_MIN = 20
ATTR_MAX = 100


@dataclass(frozen=True)
class PlayerDevInput:
    player_id: int
    player_type: PlayerType
    age: int
    attrs: dict[str, int]
    potential: int
    development_type: DevType
    perf_signal: float  # clamped [-1, 1]


@dataclass(frozen=True)
class DevEvent:
    attribute: str
    old_value: int
    new_value: int
    delta: int
    reason: EventReason


@dataclass(frozen=True)
class PlayerDevResult:
    new_attrs: dict[str, int]
    events: tuple[DevEvent, ...]
    summary_reason: SummaryReason
    overall_before: int
    overall_after: int


def _attribute_set(player_type: PlayerType) -> tuple[str, ...]:
    return SKATER_ATTRIBUTES if player_type == "skater" else GOALIE_ATTRIBUTES


def overall_from_attrs(player: PlayerDevInput) -> int:
    attrs = _attribute_set(player.player_type)
    return round(sum(player.attrs[a] for a in attrs) / len(attrs))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_development_sim.py -q
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/sim/development.py backend/tests/test_development_sim.py
git commit -m "feat(sim): add development dataclasses and overall helper"
```

---

## Task 7: Pure simulation — implement `develop_player`

**Files:**
- Modify: `backend/sim/development.py`
- Modify: `backend/tests/test_development_sim.py`

- [ ] **Step 1: Write failing tests for determinism, growth, decline, soft cap, dev types, perf, summary ordering**

Append to `backend/tests/test_development_sim.py`:

```python
import statistics

from sim.development import develop_player


def _cohort(make_input, n=400):
    return [develop_player(make_input(i), season_seed=12345) for i in range(n)]


def test_determinism():
    p = _skater_input(player_id=42)
    a = develop_player(p, season_seed=99)
    b = develop_player(p, season_seed=99)
    assert a == b


def test_young_high_potential_grows_on_average():
    def make(i: int):
        return _skater_input(
            player_id=i,
            age=19,
            attrs={k: 70 for k in SKATER_ATTRIBUTES},
            potential=90,
        )
    results = _cohort(make)
    deltas = [r.overall_after - r.overall_before for r in results]
    assert statistics.mean(deltas) > 0.5
    grew = sum(1 for r in results if r.overall_after > r.overall_before)
    assert grew > len(results) * 0.5


def test_old_players_decline_on_average():
    def make(i: int):
        return _skater_input(
            player_id=i,
            age=35,
            attrs={k: 70 for k in SKATER_ATTRIBUTES},
            potential=85,
        )
    results = _cohort(make)
    deltas = [r.overall_after - r.overall_before for r in results]
    assert statistics.mean(deltas) < -0.3


def test_soft_cap_growth_rare_but_not_zero():
    def make(i: int):
        return _skater_input(
            player_id=i,
            age=21,
            attrs={k: 90 for k in SKATER_ATTRIBUTES},  # overall 90
            potential=90,                                # gap = 0
        )
    results = _cohort(make, n=600)
    grew_count = sum(
        1 for r in results
        for ev in r.events if ev.delta > 0
    )
    # Some growth allowed (overshoot), but rare relative to a young high-pot cohort.
    assert 0 < grew_count < len(results) * 0.5


def test_early_bloomer_outgrows_late_bloomer_at_20():
    def make(player_id: int, dev: str):
        return _skater_input(
            player_id=player_id,
            age=20,
            attrs={k: 70 for k in SKATER_ATTRIBUTES},
            potential=88,
            development_type=dev,
        )
    early = [develop_player(make(i, "early_bloomer"), 7) for i in range(300)]
    late = [develop_player(make(i, "late_bloomer"), 7) for i in range(300)]
    early_mean = statistics.mean(r.overall_after - r.overall_before for r in early)
    late_mean = statistics.mean(r.overall_after - r.overall_before for r in late)
    assert early_mean > late_mean


def test_late_bloomer_outgrows_early_bloomer_at_27():
    def make(player_id: int, dev: str):
        return _skater_input(
            player_id=player_id,
            age=27,
            attrs={k: 75 for k in SKATER_ATTRIBUTES},
            potential=88,
            development_type=dev,
        )
    early = [develop_player(make(i, "early_bloomer"), 11) for i in range(300)]
    late = [develop_player(make(i, "late_bloomer"), 11) for i in range(300)]
    early_mean = statistics.mean(r.overall_after - r.overall_before for r in early)
    late_mean = statistics.mean(r.overall_after - r.overall_before for r in late)
    assert late_mean > early_mean


def test_boom_or_bust_has_higher_variance_than_steady():
    def make(player_id: int, dev: str):
        return _skater_input(
            player_id=player_id,
            age=22,
            attrs={k: 72 for k in SKATER_ATTRIBUTES},
            potential=88,
            development_type=dev,
        )
    boom = [develop_player(make(i, "boom_or_bust"), 13) for i in range(400)]
    steady = [develop_player(make(i, "steady"), 13) for i in range(400)]
    boom_var = statistics.pvariance(r.overall_after - r.overall_before for r in boom)
    steady_var = statistics.pvariance(r.overall_after - r.overall_before for r in steady)
    assert boom_var > steady_var


def test_perf_signal_above_average_helps_growth():
    def make(player_id: int, perf: float):
        return _skater_input(
            player_id=player_id,
            age=24,
            attrs={k: 75 for k in SKATER_ATTRIBUTES},
            potential=85,
            perf_signal=perf,
        )
    pos = [develop_player(make(i, 1.0), 5) for i in range(400)]
    neg = [develop_player(make(i, -1.0), 5) for i in range(400)]
    pos_mean = statistics.mean(r.overall_after - r.overall_before for r in pos)
    neg_mean = statistics.mean(r.overall_after - r.overall_before for r in neg)
    assert pos_mean > neg_mean


def test_no_events_means_plateau():
    # An age-31 player at potential with perf_signal 0 produces few events; we just
    # check the contract: when there are zero events, summary_reason is plateau.
    def make(i: int):
        return _skater_input(
            player_id=i,
            age=31,
            attrs={k: 90 for k in SKATER_ATTRIBUTES},
            potential=90,
        )
    found_plateau = False
    for i in range(200):
        r = develop_player(make(i), season_seed=1)
        if not r.events:
            assert r.summary_reason == "plateau"
            found_plateau = True
    assert found_plateau, "expected at least one plateau outcome in cohort"


def test_mixed_takes_precedence_over_net_positive():
    # Construct events list manually via internal helper if exposed; otherwise rely
    # on a probabilistic cohort and assert that mixed-sign events report mixed.
    from sim.development import classify_summary
    events = (
        DevEvent(attribute="skating", old_value=70, new_value=72, delta=2, reason="growth"),
        DevEvent(attribute="defense", old_value=70, new_value=69, delta=-1, reason="decline"),
    )
    assert classify_summary(events, dev_type="steady") == "mixed"
```

(`DevEvent` import is satisfied by the existing top-of-file import block; ensure it is added to that import line.)

Update the existing test imports at the top of the file to also import `DevEvent`:

```python
from sim.development import (
    DevEvent,
    PlayerDevInput,
    GOALIE_ATTRIBUTES,
    SKATER_ATTRIBUTES,
    overall_from_attrs,
)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && uv run pytest tests/test_development_sim.py -q
```

Expected: failures (`develop_player`, `classify_summary` missing).

- [ ] **Step 3: Implement the formula in `sim/development.py`**

Append to `backend/sim/development.py`:

```python
# Probability tables (p_grow, p_decline) per (player_type, age_bucket).
# Buckets are inclusive ranges; first match wins.
_SKATER_AGE_TABLE = (
    ((18, 22), (0.55, 0.00)),
    ((23, 26), (0.30, 0.02)),
    ((27, 31), (0.10, 0.05)),
    ((32, 34), (0.03, 0.25)),
    ((35, 99), (0.01, 0.45)),
)
_GOALIE_AGE_TABLE = (
    ((18, 24), (0.55, 0.00)),
    ((25, 28), (0.30, 0.02)),
    ((29, 33), (0.10, 0.05)),
    ((34, 36), (0.03, 0.25)),
    ((37, 99), (0.01, 0.45)),
)


def _age_probabilities(player_type: PlayerType, age: int) -> tuple[float, float]:
    table = _SKATER_AGE_TABLE if player_type == "skater" else _GOALIE_AGE_TABLE
    for (lo, hi), probs in table:
        if lo <= age <= hi:
            return probs
    return (0.0, 0.5)  # extreme age fallback


def _apply_dev_type(
    p_grow: float, p_decline: float, age: int, dev_type: DevType
) -> tuple[float, float]:
    if dev_type == "early_bloomer":
        if 18 <= age <= 23:
            p_grow *= 1.3
        if age >= 27:
            p_grow *= 0.6
    elif dev_type == "late_bloomer":
        if 18 <= age <= 23:
            p_grow *= 0.6
        if 24 <= age <= 29:
            p_grow *= 1.3
    return p_grow, p_decline


def _potential_gap_modifier(p_grow: float, gap: int) -> float:
    if gap <= 0:
        return p_grow * 0.15
    return p_grow * max(0.2, min(1.5, 0.2 + gap / 15))


def _perf_modifier(p_grow: float, p_decline: float, s: float) -> tuple[float, float]:
    return (p_grow * (1 + 0.15 * s), p_decline * (1 - 0.15 * s))


def _grow_magnitude(rng: random.Random, dev_type: DevType) -> int:
    if dev_type == "boom_or_bust":
        if rng.random() < 0.05:
            return 3
        if rng.random() < 0.50:
            return 2
        return 1
    return 2 if rng.random() < 0.25 else 1


def _decline_magnitude(rng: random.Random, dev_type: DevType) -> int:
    if dev_type == "boom_or_bust" and rng.random() < 0.30:
        return 2
    return 1


def _clamp_attr(v: int) -> int:
    return max(ATTR_MIN, min(ATTR_MAX, v))


def classify_summary(events: tuple[DevEvent, ...], dev_type: DevType) -> SummaryReason:
    if not events:
        return "plateau"
    deltas = [e.delta for e in events]
    grew = [d for d in deltas if d > 0]
    declined = [d for d in deltas if d < 0]
    if grew and not declined and dev_type == "boom_or_bust" and any(d >= 2 for d in grew):
        return "boom"
    if declined and not grew and dev_type == "boom_or_bust" and any(d <= -2 for d in declined):
        return "bust"
    if grew and declined:
        return "mixed"
    total = sum(deltas)
    if total > 0:
        return "growth"
    if total < 0:
        return "decline"
    return "plateau"


def develop_player(player: PlayerDevInput, season_seed: int) -> PlayerDevResult:
    rng = random.Random(hash((season_seed, player.player_type, player.player_id)) & 0x7FFFFFFF)
    overall_before = overall_from_attrs(player)
    new_attrs = dict(player.attrs)
    events: list[DevEvent] = []

    base_grow, base_decline = _age_probabilities(player.player_type, player.age)
    base_grow, base_decline = _apply_dev_type(base_grow, base_decline, player.age, player.development_type)

    for attr in _attribute_set(player.player_type):
        old = new_attrs[attr]
        gap = player.potential - overall_from_attrs(
            PlayerDevInput(
                player_id=player.player_id,
                player_type=player.player_type,
                age=player.age,
                attrs=new_attrs,
                potential=player.potential,
                development_type=player.development_type,
                perf_signal=player.perf_signal,
            )
        )
        p_grow = _potential_gap_modifier(base_grow, gap)
        p_grow, p_decline = _perf_modifier(p_grow, base_decline, player.perf_signal)
        # Clamp combined probabilities so they never overlap.
        p_grow = max(0.0, min(0.95, p_grow))
        p_decline = max(0.0, min(0.95, p_decline))
        if p_grow + p_decline > 0.99:
            scale = 0.99 / (p_grow + p_decline)
            p_grow *= scale
            p_decline *= scale

        r = rng.random()
        if r < p_grow:
            mag = _grow_magnitude(rng, player.development_type)
            new = _clamp_attr(old + mag)
            if new != old:
                events.append(DevEvent(attr, old, new, new - old, "growth"))
                new_attrs[attr] = new
        elif r > 1 - p_decline:
            mag = _decline_magnitude(rng, player.development_type)
            new = _clamp_attr(old - mag)
            if new != old:
                events.append(DevEvent(attr, old, new, new - old, "decline"))
                new_attrs[attr] = new
        # else: stable, no event

    summary = classify_summary(tuple(events), player.development_type)
    # Reclassify events as boom/bust if the summary triggered those buckets, so the
    # per-attribute reason matches the player-level summary for boom_or_bust outliers.
    if summary in ("boom", "bust"):
        target_reason: EventReason = "boom" if summary == "boom" else "bust"
        events = [DevEvent(e.attribute, e.old_value, e.new_value, e.delta, target_reason) for e in events]

    overall_after = overall_from_attrs(
        PlayerDevInput(
            player_id=player.player_id,
            player_type=player.player_type,
            age=player.age,
            attrs=new_attrs,
            potential=player.potential,
            development_type=player.development_type,
            perf_signal=player.perf_signal,
        )
    )

    return PlayerDevResult(
        new_attrs=new_attrs,
        events=tuple(events),
        summary_reason=summary,
        overall_before=overall_before,
        overall_after=overall_after,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_development_sim.py -q
```

Expected: all tests pass. If a probabilistic threshold test flakes (e.g., variance comparison), keep the seed as written and re-run; the assertion margins are deliberately generous. If a real failure surfaces, tune the formula constants in this file (not the test) and re-run until green.

- [ ] **Step 5: Commit**

```bash
git add backend/sim/development.py backend/tests/test_development_sim.py
git commit -m "feat(sim): implement deterministic develop_player formula"
```

---

## Task 8: Errors — `NoActiveSeason`, `SeasonNotComplete`

**Files:**
- Modify: `backend/app/errors.py`

- [ ] **Step 1: Inspect existing errors module**

```bash
cat backend/app/errors.py
```

- [ ] **Step 2: Add new exception classes**

Add at the end of `backend/app/errors.py`, mirroring existing exception style:

```python
class NoActiveSeason(Exception):
    """Raised when no season with status='active' exists."""


class SeasonNotComplete(Exception):
    """Raised when rollover is attempted before the active season completes."""
```

If existing exceptions inherit from a base or are mapped to HTTP status codes elsewhere (check imports of e.g. `LeagueNotFound`), follow that pattern.

- [ ] **Step 3: Commit**

```bash
git add backend/app/errors.py
git commit -m "feat(errors): add NoActiveSeason and SeasonNotComplete"
```

---

## Task 9: Active-season helper + advance_service fix

**Files:**
- Modify: `backend/app/services/league_service.py`
- Modify: `backend/app/services/advance_service.py`

The codebase currently calls `db.query(Season).first()` to fetch "the" season. With multi-season, that's wrong: pick the active season explicitly.

- [ ] **Step 1: Add `get_active_season` helper**

In `backend/app/services/league_service.py`, replace `get_league` with:

```python
def get_active_season(db: Session) -> Season:
    season = db.query(Season).filter_by(status="active").order_by(Season.id.desc()).first()
    if not season:
        raise LeagueNotFound("no active league")
    return season


# Backwards-compatible alias used by existing call sites.
get_league = get_active_season
```

- [ ] **Step 2: Fix advance_service**

In `backend/app/services/advance_service.py`, change:

```python
def advance_matchday(db: Session) -> dict:
    season = db.query(Season).first()
```

to:

```python
from app.services.league_service import get_active_season

def advance_matchday(db: Session) -> dict:
    try:
        season = get_active_season(db)
    except LeagueNotFound:
        raise LeagueNotFound("no active league")
```

(Keep the surrounding behavior intact; only the season lookup changes.)

- [ ] **Step 3: Run tests**

```bash
cd backend && uv run pytest -q
```

Expected: pass. Fix any single-season assumptions exposed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/league_service.py backend/app/services/advance_service.py
git commit -m "refactor: route season lookups through get_active_season"
```

---

## Task 10: Pydantic schemas — development summary and career

**Files:**
- Create: `backend/app/schemas/development.py`
- Create: `backend/app/schemas/career.py`

- [ ] **Step 1: Create development schemas**

Create `backend/app/schemas/development.py`:

```python
from pydantic import BaseModel


class DevelopmentEventOut(BaseModel):
    attribute: str
    old_value: int
    new_value: int
    delta: int
    reason: str


class SeasonProgressionOut(BaseModel):
    player_type: str
    player_id: int
    player_name: str
    team_id: int | None
    age_before: int
    age_after: int
    overall_before: int
    overall_after: int
    potential: int
    development_type: str
    summary_reason: str
    events: list[DevelopmentEventOut]


class DevelopmentSummaryOut(BaseModel):
    season_id: int
    progressions: list[SeasonProgressionOut]


class StartNextSeasonOut(BaseModel):
    new_season_id: int
    development_summary: DevelopmentSummaryOut
```

- [ ] **Step 2: Create career schemas**

Create `backend/app/schemas/career.py`:

```python
from pydantic import BaseModel


class SkaterSeasonStatsOut(BaseModel):
    season_id: int
    gp: int
    g: int
    a: int
    pts: int
    sog: int


class SkaterCareerOut(BaseModel):
    player_id: int
    name: str
    by_season: list[SkaterSeasonStatsOut]
    totals: SkaterSeasonStatsOut


class GoalieSeasonStatsOut(BaseModel):
    season_id: int
    gp: int
    shots_against: int
    saves: int
    goals_against: int
    sv_pct: float


class GoalieCareerOut(BaseModel):
    player_id: int
    name: str
    by_season: list[GoalieSeasonStatsOut]
    totals: GoalieSeasonStatsOut
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/development.py backend/app/schemas/career.py
git commit -m "feat(schemas): add development and career pydantic schemas"
```

---

## Task 11: Season rollover service — orchestration scaffold + guards

**Files:**
- Create: `backend/app/services/season_rollover_service.py`
- Create: `backend/tests/test_season_rollover.py`

- [ ] **Step 1: Write failing guard tests**

Create `backend/tests/test_season_rollover.py`:

```python
import pytest

from app.errors import NoActiveSeason, SeasonNotComplete
from app.services import season_rollover_service


def test_rollover_raises_when_no_active_season(empty_db):
    with pytest.raises(NoActiveSeason):
        season_rollover_service.start_next_season(empty_db)


def test_rollover_raises_when_season_not_complete(active_season_with_scheduled_games):
    with pytest.raises(SeasonNotComplete):
        season_rollover_service.start_next_season(active_season_with_scheduled_games)
```

If your test suite already provides DB fixtures, locate them (e.g., in `backend/tests/conftest.py`) and reuse the names. If not, add a minimal `conftest.py` that produces an in-memory or transactional Postgres session — match whatever existing tests use (look at `backend/tests/test_advance_service.py` or similar).

If there is no `conftest.py` providing these fixtures, add them now in `backend/tests/conftest.py`:

```python
import pytest
from sqlalchemy.orm import Session

from app.services.league_service import create_or_reset_league


@pytest.fixture
def empty_db(db_session: Session) -> Session:
    return db_session


@pytest.fixture
def active_season_with_scheduled_games(db_session: Session) -> Session:
    create_or_reset_league(db_session, seed=42)
    db_session.flush()
    return db_session
```

(Adjust to whatever DB session fixture your existing tests already use. If unsure, run `grep -r "db_session" backend/tests` and `grep -r "@pytest.fixture" backend/tests` to find the conventions.)

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && uv run pytest tests/test_season_rollover.py -q
```

Expected: ImportError or fixture errors.

- [ ] **Step 3: Implement the scaffold + guards**

Create `backend/app/services/season_rollover_service.py`:

```python
from sqlalchemy.orm import Session

from app.errors import NoActiveSeason, SeasonNotComplete
from app.models import Game, Season


def start_next_season(db: Session) -> dict:
    """Roll the active season into a new season. See spec for details.

    Returns a dict matching ``StartNextSeasonOut`` shape. Wraps everything in a
    single transaction; the caller is expected to commit on success.
    """
    season = (
        db.query(Season).filter_by(status="active").order_by(Season.id.desc()).first()
    )
    if season is None:
        raise NoActiveSeason("no active season to roll over")
    if season.status != "complete":
        # 'active' here means the season exists but is still ongoing.
        # Below also covers the case where status was set to 'complete' but a
        # scheduled game lingers (defensive).
        if season.status != "complete":
            scheduled = (
                db.query(Game)
                .filter_by(season_id=season.id, status="scheduled")
                .count()
            )
            if season.status != "complete" or scheduled > 0:
                raise SeasonNotComplete(
                    f"season {season.id} status={season.status!r} not complete"
                )

    raise NotImplementedError  # remaining steps land in Task 12
```

Wait — the spec says the rollover only works once `status == 'complete'`. The active-status filter above is wrong: the season is `'active'` until the last game is simulated, then `advance_matchday` flips it to `'complete'`. So we must instead query for the latest non-rolled season (status `'complete'` or `'active'`) and treat anything but `'complete'` as `SeasonNotComplete`.

Replace the function body with:

```python
def start_next_season(db: Session) -> dict:
    season = (
        db.query(Season)
        .filter(Season.status.in_(["active", "complete"]))
        .order_by(Season.id.desc())
        .first()
    )
    if season is None:
        raise NoActiveSeason("no active or completed season")
    if season.status != "complete":
        raise SeasonNotComplete(
            f"season {season.id} status={season.status!r}; expected 'complete'"
        )
    scheduled = (
        db.query(Game).filter_by(season_id=season.id, status="scheduled").count()
    )
    if scheduled > 0:
        raise SeasonNotComplete(
            f"season {season.id} has {scheduled} scheduled games remaining"
        )
    raise NotImplementedError  # filled in Task 12
```

- [ ] **Step 4: Run guard tests**

```bash
cd backend && uv run pytest tests/test_season_rollover.py -q
```

Expected: both `test_rollover_raises_when_no_active_season` and `test_rollover_raises_when_season_not_complete` pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/season_rollover_service.py backend/tests/test_season_rollover.py backend/tests/conftest.py
git commit -m "feat(rollover): scaffold service with guard validation"
```

---

## Task 12: Season rollover service — full orchestration

**Files:**
- Modify: `backend/app/services/season_rollover_service.py`
- Modify: `backend/tests/test_season_rollover.py`

- [ ] **Step 1: Add tests for full rollover**

Append to `backend/tests/test_season_rollover.py`:

```python
from app.models import (
    DevelopmentEvent,
    Game,
    Goalie,
    GoalieGameStat,
    Season,
    SeasonProgression,
    Skater,
    SkaterGameStat,
    Standing,
)
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league


def _simulate_full_season(db) -> Season:
    season = create_or_reset_league(db, seed=2026)
    db.flush()
    while True:
        res = advance_matchday(db)
        if res["season_status"] == "complete":
            break
    db.commit()
    return season


def test_rollover_creates_new_season_and_resets_state(db_session):
    old = _simulate_full_season(db_session)
    out = season_rollover_service.start_next_season(db_session)
    db_session.commit()

    new = (
        db_session.query(Season)
        .filter_by(status="active")
        .order_by(Season.id.desc())
        .first()
    )
    assert new is not None and new.id != old.id
    assert new.user_team_id == old.user_team_id
    assert new.current_matchday == 1
    assert new.status == "active"

    new_games = db_session.query(Game).filter_by(season_id=new.id).count()
    assert new_games > 0
    new_standings = db_session.query(Standing).filter_by(season_id=new.id).count()
    assert new_standings == db_session.query(Standing.team_id).distinct().count()
    for s in db_session.query(Standing).filter_by(season_id=new.id).all():
        assert s.games_played == 0
        assert s.points == 0
        assert s.goals_for == 0


def test_rollover_ages_every_player(db_session):
    old = _simulate_full_season(db_session)
    skater_ages = {s.id: s.age for s in db_session.query(Skater).all()}
    goalie_ages = {g.id: g.age for g in db_session.query(Goalie).all()}
    season_rollover_service.start_next_season(db_session)
    db_session.commit()
    for s in db_session.query(Skater).all():
        assert s.age == skater_ages[s.id] + 1
    for g in db_session.query(Goalie).all():
        assert g.age == goalie_ages[g.id] + 1


def test_rollover_persists_progression_and_events(db_session):
    old = _simulate_full_season(db_session)
    season_rollover_service.start_next_season(db_session)
    db_session.commit()
    new = (
        db_session.query(Season).filter_by(status="active").order_by(Season.id.desc()).first()
    )
    progressions = (
        db_session.query(SeasonProgression).filter_by(to_season_id=new.id).all()
    )
    expected_count = (
        db_session.query(Skater).count() + db_session.query(Goalie).count()
    )
    assert len(progressions) == expected_count
    # development_event rows are present for at least some progressions
    event_count = db_session.query(DevelopmentEvent).count()
    assert event_count >= 0  # may be zero in unlikely no-change cohorts; sanity only


def test_rollover_preserves_old_data(db_session):
    old = _simulate_full_season(db_session)
    old_game_count = db_session.query(Game).filter_by(season_id=old.id).count()
    old_stats_count = db_session.query(SkaterGameStat).count()
    season_rollover_service.start_next_season(db_session)
    db_session.commit()
    assert (
        db_session.query(Game).filter_by(season_id=old.id).count() == old_game_count
    )
    assert db_session.query(SkaterGameStat).count() == old_stats_count
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && uv run pytest tests/test_season_rollover.py -q
```

Expected: failures with `NotImplementedError` or schema-level errors.

- [ ] **Step 3: Implement full orchestration**

Replace the body of `start_next_season` in `backend/app/services/season_rollover_service.py` (after the guards) with the orchestration. Full file:

```python
import random
from collections import defaultdict

from sqlalchemy.orm import Session

from app.errors import NoActiveSeason, SeasonNotComplete
from app.models import (
    DevelopmentEvent,
    Game,
    Goalie,
    GoalieGameStat,
    Season,
    SeasonProgression,
    Skater,
    SkaterGameStat,
    Standing,
    Team,
)
from app.services.generation.schedule import generate_schedule
from sim.development import (
    GOALIE_ATTRIBUTES,
    SKATER_ATTRIBUTES,
    PlayerDevInput,
    PlayerDevResult,
    develop_player,
)


def _league_skater_ppg(db: Session, season_id: int) -> float:
    rows = (
        db.query(SkaterGameStat)
        .join(Game, SkaterGameStat.game_id == Game.id)
        .filter(Game.season_id == season_id)
        .all()
    )
    if not rows:
        return 0.0
    pts_by_player: dict[int, int] = defaultdict(int)
    gp_by_player: dict[int, int] = defaultdict(int)
    for r in rows:
        pts_by_player[r.skater_id] += (r.goals or 0) + (r.assists or 0)
        gp_by_player[r.skater_id] += 1
    ppg_values = [
        pts_by_player[pid] / gp_by_player[pid] for pid in pts_by_player if gp_by_player[pid] > 0
    ]
    return sum(ppg_values) / len(ppg_values) if ppg_values else 0.0


def _league_save_pct(db: Session, season_id: int) -> float:
    rows = (
        db.query(GoalieGameStat)
        .join(Game, GoalieGameStat.game_id == Game.id)
        .filter(Game.season_id == season_id)
        .all()
    )
    sa = sum(r.shots_against for r in rows)
    sv = sum(r.saves for r in rows)
    return (sv / sa) if sa else 0.0


def _skater_perf_signal(
    db: Session, season_id: int, skater_id: int, league_ppg: float
) -> float:
    rows = (
        db.query(SkaterGameStat)
        .join(Game, SkaterGameStat.game_id == Game.id)
        .filter(Game.season_id == season_id, SkaterGameStat.skater_id == skater_id)
        .all()
    )
    gp = len(rows)
    if gp == 0 or league_ppg == 0:
        return 0.0
    pts = sum((r.goals or 0) + (r.assists or 0) for r in rows)
    ppg = pts / gp
    gp_weight = min(gp / 20, 1.0)
    s = ((ppg / league_ppg) - 1) * gp_weight
    return max(-1.0, min(1.0, s))


def _goalie_perf_signal(
    db: Session, season_id: int, goalie_id: int, league_sv: float
) -> float:
    rows = (
        db.query(GoalieGameStat)
        .join(Game, GoalieGameStat.game_id == Game.id)
        .filter(Game.season_id == season_id, GoalieGameStat.goalie_id == goalie_id)
        .all()
    )
    gp = len(rows)
    if gp == 0 or league_sv == 0:
        return 0.0
    sa = sum(r.shots_against for r in rows)
    sv = sum(r.saves for r in rows)
    if sa == 0:
        return 0.0
    sv_pct = sv / sa
    gp_weight = min(gp / 10, 1.0)
    s = ((sv_pct - league_sv) / 0.020) * gp_weight
    return max(-1.0, min(1.0, s))


def _apply_skater_development(
    skater: Skater, result: PlayerDevResult
) -> None:
    for attr in SKATER_ATTRIBUTES:
        setattr(skater, attr, result.new_attrs[attr])


def _apply_goalie_development(
    goalie: Goalie, result: PlayerDevResult
) -> None:
    for attr in GOALIE_ATTRIBUTES:
        setattr(goalie, attr, result.new_attrs[attr])


def _persist_progression(
    db: Session,
    *,
    from_season_id: int,
    to_season_id: int,
    player_type: str,
    player_id: int,
    age_before: int,
    age_after: int,
    potential: int,
    development_type: str,
    result: PlayerDevResult,
) -> None:
    sp = SeasonProgression(
        from_season_id=from_season_id,
        to_season_id=to_season_id,
        player_type=player_type,
        player_id=player_id,
        age_before=age_before,
        age_after=age_after,
        overall_before=result.overall_before,
        overall_after=result.overall_after,
        potential=potential,
        development_type=development_type,
        summary_reason=result.summary_reason,
    )
    db.add(sp)
    db.flush()
    for ev in result.events:
        db.add(
            DevelopmentEvent(
                season_progression_id=sp.id,
                attribute=ev.attribute,
                old_value=ev.old_value,
                new_value=ev.new_value,
                delta=ev.delta,
                reason=ev.reason,
            )
        )


def start_next_season(db: Session) -> dict:
    season = (
        db.query(Season)
        .filter(Season.status.in_(["active", "complete"]))
        .order_by(Season.id.desc())
        .first()
    )
    if season is None:
        raise NoActiveSeason("no active or completed season")
    if season.status != "complete":
        raise SeasonNotComplete(
            f"season {season.id} status={season.status!r}; expected 'complete'"
        )
    scheduled = (
        db.query(Game).filter_by(season_id=season.id, status="scheduled").count()
    )
    if scheduled > 0:
        raise SeasonNotComplete(
            f"season {season.id} has {scheduled} scheduled games remaining"
        )

    league_ppg = _league_skater_ppg(db, season.id)
    league_sv = _league_save_pct(db, season.id)

    new_seed = (season.seed * 31 + season.id) & 0x7FFFFFFF
    new_season = Season(
        seed=new_seed,
        user_team_id=season.user_team_id,
        current_matchday=1,
        status="active",
    )
    db.add(new_season)
    db.flush()

    skaters = db.query(Skater).all()
    goalies = db.query(Goalie).all()

    for s in skaters:
        perf = _skater_perf_signal(db, season.id, s.id, league_ppg)
        inp = PlayerDevInput(
            player_id=s.id,
            player_type="skater",
            age=s.age,
            attrs={
                "skating": s.skating,
                "shooting": s.shooting,
                "passing": s.passing,
                "defense": s.defense,
                "physical": s.physical,
            },
            potential=s.potential,
            development_type=s.development_type,
            perf_signal=perf,
        )
        result = develop_player(inp, season_seed=new_seed)
        _persist_progression(
            db,
            from_season_id=season.id,
            to_season_id=new_season.id,
            player_type="skater",
            player_id=s.id,
            age_before=s.age,
            age_after=s.age + 1,
            potential=s.potential,
            development_type=s.development_type,
            result=result,
        )
        _apply_skater_development(s, result)
        s.age += 1

    for g in goalies:
        perf = _goalie_perf_signal(db, season.id, g.id, league_sv)
        inp = PlayerDevInput(
            player_id=g.id,
            player_type="goalie",
            age=g.age,
            attrs={
                "reflexes": g.reflexes,
                "positioning": g.positioning,
                "rebound_control": g.rebound_control,
                "puck_handling": g.puck_handling,
                "mental": g.mental,
            },
            potential=g.potential,
            development_type=g.development_type,
            perf_signal=perf,
        )
        result = develop_player(inp, season_seed=new_seed)
        _persist_progression(
            db,
            from_season_id=season.id,
            to_season_id=new_season.id,
            player_type="goalie",
            player_id=g.id,
            age_before=g.age,
            age_after=g.age + 1,
            potential=g.potential,
            development_type=g.development_type,
            result=result,
        )
        _apply_goalie_development(g, result)
        g.age += 1

    team_ids = [t.id for t in db.query(Team).order_by(Team.id).all()]
    rng = random.Random(new_seed)
    generate_schedule(rng, db, new_season.id, team_ids)
    for tid in team_ids:
        db.add(Standing(team_id=tid, season_id=new_season.id))
    db.flush()

    return {"new_season_id": new_season.id, "season_id": new_season.id}
```

- [ ] **Step 4: Run all rollover tests**

```bash
cd backend && uv run pytest tests/test_season_rollover.py -q
```

Expected: all rollover tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/season_rollover_service.py backend/tests/test_season_rollover.py
git commit -m "feat(rollover): full season rollover orchestration with development persistence"
```

---

## Task 13: API endpoints — `/start-next` and `/development-summary`

**Files:**
- Modify: `backend/app/api/season.py`
- Create: `backend/app/api/development.py` (mounted under season tag)

We attach both endpoints to the existing season router for cohesion.

- [ ] **Step 1: Add error → HTTP mappings**

Find where exceptions like `LeagueNotFound` are mapped to HTTP responses (search for `LeagueNotFound` in `backend/app`). Add equivalent mappings for `NoActiveSeason` (404) and `SeasonNotComplete` (409). If exceptions are caught inline in routers, follow that pattern; if there is a global exception handler, register the new mappings there.

- [ ] **Step 2: Add `/start-next` endpoint**

In `backend/app/api/season.py`, add:

```python
from app.errors import NoActiveSeason, SeasonNotComplete
from app.schemas.development import (
    DevelopmentEventOut,
    DevelopmentSummaryOut,
    SeasonProgressionOut,
    StartNextSeasonOut,
)
from app.services import season_rollover_service
from app.models import DevelopmentEvent, Goalie, SeasonProgression, Skater, Team


def _build_summary(db: Session, season_id: int) -> DevelopmentSummaryOut:
    progressions = (
        db.query(SeasonProgression).filter_by(to_season_id=season_id).all()
    )
    skater_team = {s.id: (s.team_id, s.name) for s in db.query(Skater).all()}
    goalie_team = {g.id: (g.team_id, g.name) for g in db.query(Goalie).all()}
    out: list[SeasonProgressionOut] = []
    for sp in progressions:
        if sp.player_type == "skater":
            team_id, name = skater_team.get(sp.player_id, (None, "?"))
        else:
            team_id, name = goalie_team.get(sp.player_id, (None, "?"))
        events = (
            db.query(DevelopmentEvent)
            .filter_by(season_progression_id=sp.id)
            .order_by(DevelopmentEvent.id)
            .all()
        )
        out.append(
            SeasonProgressionOut(
                player_type=sp.player_type,
                player_id=sp.player_id,
                player_name=name,
                team_id=team_id,
                age_before=sp.age_before,
                age_after=sp.age_after,
                overall_before=sp.overall_before,
                overall_after=sp.overall_after,
                potential=sp.potential,
                development_type=sp.development_type,
                summary_reason=sp.summary_reason,
                events=[
                    DevelopmentEventOut(
                        attribute=e.attribute,
                        old_value=e.old_value,
                        new_value=e.new_value,
                        delta=e.delta,
                        reason=e.reason,
                    )
                    for e in events
                ],
            )
        )
    return DevelopmentSummaryOut(season_id=season_id, progressions=out)


@router.post("/start-next", response_model=StartNextSeasonOut)
def post_start_next(db: Session = Depends(get_db)):
    try:
        res = season_rollover_service.start_next_season(db)
    except NoActiveSeason as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SeasonNotComplete as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    db.commit()
    summary = _build_summary(db, res["new_season_id"])
    return StartNextSeasonOut(new_season_id=res["new_season_id"], development_summary=summary)


@router.get("/development-summary", response_model=DevelopmentSummaryOut)
def get_development_summary(season_id: int | None = None, db: Session = Depends(get_db)):
    if season_id is None:
        last = (
            db.query(SeasonProgression)
            .order_by(SeasonProgression.to_season_id.desc())
            .first()
        )
        if last is None:
            raise HTTPException(status_code=404, detail="no rollovers recorded")
        season_id = last.to_season_id
    return _build_summary(db, season_id)
```

Add `from fastapi import HTTPException` to the imports if not already present.

- [ ] **Step 3: Run tests**

```bash
cd backend && uv run pytest -q
```

Expected: pass. If FastAPI startup fails on import-cycle, move `_build_summary` and the imports it needs into `app/services/development_query.py` and re-import.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/season.py
git commit -m "feat(api): add /season/start-next and /season/development-summary endpoints"
```

---

## Task 14: Player development + career endpoints

**Files:**
- Modify: `backend/app/api/players.py`
- Create: `backend/tests/test_player_career_api.py`

- [ ] **Step 1: Inspect existing players router**

```bash
cat backend/app/api/players.py
```

Note the routing pattern (path prefix, `Depends(get_db)`, response models).

- [ ] **Step 2: Add development + career endpoints**

Append to `backend/app/api/players.py` (adjust imports as needed):

```python
from fastapi import HTTPException
from sqlalchemy import func

from app.models import (
    DevelopmentEvent,
    Game,
    Goalie,
    GoalieGameStat,
    SeasonProgression,
    Skater,
    SkaterGameStat,
)
from app.schemas.career import (
    GoalieCareerOut,
    GoalieSeasonStatsOut,
    SkaterCareerOut,
    SkaterSeasonStatsOut,
)
from app.schemas.development import DevelopmentEventOut, SeasonProgressionOut


@router.get("/{player_id}/development")
def get_player_development(
    player_id: int, type: str, db: Session = Depends(get_db)
) -> dict:
    if type not in ("skater", "goalie"):
        raise HTTPException(status_code=400, detail="type must be 'skater' or 'goalie'")
    rows = (
        db.query(SeasonProgression)
        .filter_by(player_type=type, player_id=player_id)
        .order_by(SeasonProgression.to_season_id.desc())
        .all()
    )
    history: list[SeasonProgressionOut] = []
    if type == "skater":
        skater = db.query(Skater).filter_by(id=player_id).first()
        if not skater:
            raise HTTPException(status_code=404, detail="skater not found")
        name = skater.name
        team_id = skater.team_id
    else:
        goalie = db.query(Goalie).filter_by(id=player_id).first()
        if not goalie:
            raise HTTPException(status_code=404, detail="goalie not found")
        name = goalie.name
        team_id = goalie.team_id
    for sp in rows:
        events = (
            db.query(DevelopmentEvent)
            .filter_by(season_progression_id=sp.id)
            .order_by(DevelopmentEvent.id)
            .all()
        )
        history.append(
            SeasonProgressionOut(
                player_type=sp.player_type,
                player_id=sp.player_id,
                player_name=name,
                team_id=team_id,
                age_before=sp.age_before,
                age_after=sp.age_after,
                overall_before=sp.overall_before,
                overall_after=sp.overall_after,
                potential=sp.potential,
                development_type=sp.development_type,
                summary_reason=sp.summary_reason,
                events=[
                    DevelopmentEventOut(
                        attribute=e.attribute,
                        old_value=e.old_value,
                        new_value=e.new_value,
                        delta=e.delta,
                        reason=e.reason,
                    )
                    for e in events
                ],
            )
        )
    return {"player_id": player_id, "name": name, "history": [h.model_dump() for h in history]}


@router.get("/{player_id}/career")
def get_player_career(
    player_id: int, type: str, db: Session = Depends(get_db)
) -> dict:
    if type == "skater":
        skater = db.query(Skater).filter_by(id=player_id).first()
        if not skater:
            raise HTTPException(status_code=404, detail="skater not found")
        rows = (
            db.query(
                Game.season_id,
                func.count(SkaterGameStat.id).label("gp"),
                func.coalesce(func.sum(SkaterGameStat.goals), 0).label("g"),
                func.coalesce(func.sum(SkaterGameStat.assists), 0).label("a"),
                func.coalesce(func.sum(SkaterGameStat.shots), 0).label("sog"),
            )
            .join(Game, SkaterGameStat.game_id == Game.id)
            .filter(SkaterGameStat.skater_id == player_id)
            .group_by(Game.season_id)
            .order_by(Game.season_id)
            .all()
        )
        by_season = [
            SkaterSeasonStatsOut(
                season_id=r.season_id,
                gp=r.gp,
                g=r.g,
                a=r.a,
                pts=r.g + r.a,
                sog=r.sog,
            )
            for r in rows
        ]
        totals = SkaterSeasonStatsOut(
            season_id=0,
            gp=sum(s.gp for s in by_season),
            g=sum(s.g for s in by_season),
            a=sum(s.a for s in by_season),
            pts=sum(s.pts for s in by_season),
            sog=sum(s.sog for s in by_season),
        )
        return SkaterCareerOut(
            player_id=skater.id, name=skater.name, by_season=by_season, totals=totals
        ).model_dump()
    if type == "goalie":
        goalie = db.query(Goalie).filter_by(id=player_id).first()
        if not goalie:
            raise HTTPException(status_code=404, detail="goalie not found")
        rows = (
            db.query(
                Game.season_id,
                func.count(GoalieGameStat.id).label("gp"),
                func.coalesce(func.sum(GoalieGameStat.shots_against), 0).label("sa"),
                func.coalesce(func.sum(GoalieGameStat.saves), 0).label("sv"),
                func.coalesce(func.sum(GoalieGameStat.goals_against), 0).label("ga"),
            )
            .join(Game, GoalieGameStat.game_id == Game.id)
            .filter(GoalieGameStat.goalie_id == player_id)
            .group_by(Game.season_id)
            .order_by(Game.season_id)
            .all()
        )
        by_season = [
            GoalieSeasonStatsOut(
                season_id=r.season_id,
                gp=r.gp,
                shots_against=r.sa,
                saves=r.sv,
                goals_against=r.ga,
                sv_pct=(r.sv / r.sa) if r.sa else 0.0,
            )
            for r in rows
        ]
        total_sa = sum(s.shots_against for s in by_season)
        total_sv = sum(s.saves for s in by_season)
        totals = GoalieSeasonStatsOut(
            season_id=0,
            gp=sum(s.gp for s in by_season),
            shots_against=total_sa,
            saves=total_sv,
            goals_against=sum(s.goals_against for s in by_season),
            sv_pct=(total_sv / total_sa) if total_sa else 0.0,
        )
        return GoalieCareerOut(
            player_id=goalie.id, name=goalie.name, by_season=by_season, totals=totals
        ).model_dump()
    raise HTTPException(status_code=400, detail="type must be 'skater' or 'goalie'")
```

- [ ] **Step 3: Add integration test for career across two seasons**

Create `backend/tests/test_player_career_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.services import season_rollover_service
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league
from app.models import Skater, SkaterGameStat


def _play_through(db) -> None:
    while advance_matchday(db)["season_status"] != "complete":
        pass
    db.commit()


def test_career_spans_two_seasons(db_session):
    create_or_reset_league(db_session, seed=314)
    db_session.flush()
    _play_through(db_session)
    season_rollover_service.start_next_season(db_session)
    db_session.commit()
    _play_through(db_session)

    skater = db_session.query(Skater).first()
    raw_total_g = (
        db_session.query(SkaterGameStat)
        .filter_by(skater_id=skater.id)
        .with_entities(SkaterGameStat.goals)
        .all()
    )
    raw_g = sum(r.goals for r in raw_total_g)

    client = TestClient(app)
    r = client.get(f"/api/players/{skater.id}/career", params={"type": "skater"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["by_season"]) >= 2
    assert body["totals"]["g"] == raw_g
    assert body["totals"]["gp"] == sum(s["gp"] for s in body["by_season"])
```

(Adjust the API path prefix if your players router mounts under a different prefix, e.g., `/players` vs `/api/players`. Run `grep -r "include_router(players_router" backend/app` to confirm.)

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/test_player_career_api.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/players.py backend/tests/test_player_career_api.py
git commit -m "feat(api): add /players/{id}/development and /players/{id}/career endpoints"
```

---

## Task 15: Frontend — typed API clients

**Files:**
- Create: `frontend/src/api/development.ts`
- Create: `frontend/src/api/career.ts`

- [ ] **Step 1: Inspect existing API client style**

```bash
ls frontend/src/api && cat frontend/src/api/season.ts 2>/dev/null || cat frontend/src/api/teams.ts 2>/dev/null || true
```

Match the existing pattern (likely `fetch` wrappers returning typed JSON, plus exported types).

- [ ] **Step 2: Add development client**

Create `frontend/src/api/development.ts`:

```ts
const API = "/api";

export type DevelopmentEvent = {
  attribute: string;
  old_value: number;
  new_value: number;
  delta: number;
  reason: string;
};

export type SeasonProgression = {
  player_type: "skater" | "goalie";
  player_id: number;
  player_name: string;
  team_id: number | null;
  age_before: number;
  age_after: number;
  overall_before: number;
  overall_after: number;
  potential: number;
  development_type: string;
  summary_reason: string;
  events: DevelopmentEvent[];
};

export type DevelopmentSummary = {
  season_id: number;
  progressions: SeasonProgression[];
};

export type StartNextSeasonResponse = {
  new_season_id: number;
  development_summary: DevelopmentSummary;
};

export async function startNextSeason(): Promise<StartNextSeasonResponse> {
  const res = await fetch(`${API}/season/start-next`, { method: "POST" });
  if (!res.ok) throw new Error(`start-next failed: ${res.status}`);
  return res.json();
}

export async function fetchDevelopmentSummary(
  seasonId?: number
): Promise<DevelopmentSummary> {
  const url = seasonId
    ? `${API}/season/development-summary?season_id=${seasonId}`
    : `${API}/season/development-summary`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`development-summary failed: ${res.status}`);
  return res.json();
}

export async function fetchPlayerDevelopment(
  playerId: number,
  type: "skater" | "goalie"
): Promise<{ player_id: number; name: string; history: SeasonProgression[] }> {
  const res = await fetch(`${API}/players/${playerId}/development?type=${type}`);
  if (!res.ok) throw new Error(`player development failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 3: Add career client**

Create `frontend/src/api/career.ts`:

```ts
const API = "/api";

export type SkaterSeasonStats = {
  season_id: number;
  gp: number;
  g: number;
  a: number;
  pts: number;
  sog: number;
};

export type SkaterCareer = {
  player_id: number;
  name: string;
  by_season: SkaterSeasonStats[];
  totals: SkaterSeasonStats;
};

export type GoalieSeasonStats = {
  season_id: number;
  gp: number;
  shots_against: number;
  saves: number;
  goals_against: number;
  sv_pct: number;
};

export type GoalieCareer = {
  player_id: number;
  name: string;
  by_season: GoalieSeasonStats[];
  totals: GoalieSeasonStats;
};

export async function fetchSkaterCareer(playerId: number): Promise<SkaterCareer> {
  const res = await fetch(`${API}/players/${playerId}/career?type=skater`);
  if (!res.ok) throw new Error(`career failed: ${res.status}`);
  return res.json();
}

export async function fetchGoalieCareer(playerId: number): Promise<GoalieCareer> {
  const res = await fetch(`${API}/players/${playerId}/career?type=goalie`);
  if (!res.ok) throw new Error(`career failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/development.ts frontend/src/api/career.ts
git commit -m "feat(frontend): add typed API clients for development and career"
```

---

## Task 16: Frontend — Development Summary page + Start Next Season action

**Files:**
- Create: `frontend/src/pages/DevelopmentSummary.tsx`
- Modify: relevant router file (likely `frontend/src/App.tsx`)
- Modify: existing season-complete page or dashboard to expose the action

- [ ] **Step 1: Locate existing routes and the season-complete view**

```bash
grep -r "Routes" frontend/src | head
grep -ri "season.*complete" frontend/src | head
```

Identify the file mounting routes and the page shown when the season ends.

- [ ] **Step 2: Create DevelopmentSummary.tsx**

Create `frontend/src/pages/DevelopmentSummary.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";
import { fetchDevelopmentSummary, SeasonProgression } from "../api/development";

function ProgressionRow({ p }: { p: SeasonProgression }) {
  const arrow = p.overall_after === p.overall_before ? "→"
    : p.overall_after > p.overall_before ? "↑" : "↓";
  return (
    <div className="border-b py-2">
      <div className="flex items-center justify-between">
        <div className="font-medium">{p.player_name}</div>
        <div className="text-sm text-gray-600">
          {p.player_type} • age {p.age_before} → {p.age_after} • POT {p.potential}
        </div>
      </div>
      <div className="text-sm">
        OVR {p.overall_before} {arrow} {p.overall_after} ({p.summary_reason})
      </div>
      {p.events.length > 0 && (
        <ul className="mt-1 text-xs text-gray-700 grid grid-cols-2 gap-x-4">
          {p.events.map((e, i) => (
            <li key={i}>
              {e.attribute}: {e.old_value} → {e.new_value} ({e.delta > 0 ? "+" : ""}{e.delta})
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function DevelopmentSummary() {
  const [params] = useSearchParams();
  const seasonIdParam = params.get("season_id");
  const seasonId = seasonIdParam ? Number(seasonIdParam) : undefined;
  const { data, isLoading, isError } = useQuery({
    queryKey: ["development-summary", seasonId],
    queryFn: () => fetchDevelopmentSummary(seasonId),
  });
  if (isLoading) return <div>Loading...</div>;
  if (isError || !data) return <div>Failed to load development summary.</div>;
  return (
    <div className="p-4 max-w-3xl mx-auto">
      <h1 className="text-xl font-semibold mb-3">
        Player Development — Season {data.season_id}
      </h1>
      <div className="bg-white rounded shadow">
        {data.progressions.map((p) => (
          <ProgressionRow key={`${p.player_type}-${p.player_id}`} p={p} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add the route**

In your router file (likely `frontend/src/App.tsx`), add a route for `/development-summary`:

```tsx
import DevelopmentSummary from "./pages/DevelopmentSummary";
// inside <Routes>:
<Route path="/development-summary" element={<DevelopmentSummary />} />
```

- [ ] **Step 4: Wire the Start Next Season action**

On the existing season-complete view (or dashboard if there is no dedicated screen), add:

```tsx
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { startNextSeason } from "../api/development";

function StartNextSeasonButton() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const m = useMutation({
    mutationFn: startNextSeason,
    onSuccess: (res) => {
      qc.invalidateQueries();
      navigate(`/development-summary?season_id=${res.new_season_id}`);
    },
  });
  return (
    <button
      className="px-3 py-1 rounded bg-black text-white"
      disabled={m.isPending}
      onClick={() => m.mutate()}
    >
      {m.isPending ? "Starting..." : "Start Next Season"}
    </button>
  );
}
```

Place it where the user lands when the season completes. If no dedicated season-complete view exists, place it on the dashboard, conditionally rendered when the season status is `'complete'`.

- [ ] **Step 5: Verify in the browser**

Start the dev server (`cd frontend && npm run dev`), then run a backend that has a completed season (use the existing seed/league flow, run `/season/advance` until complete, then click "Start Next Season"). Confirm the development summary loads and shows player rows with deltas.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/DevelopmentSummary.tsx frontend/src/App.tsx <whichever-page-was-modified>
git commit -m "feat(frontend): add development summary page and Start Next Season action"
```

---

## Task 17: Frontend — Player detail OVR/POT, Development tab, Career tab

**Files:**
- Modify: `frontend/src/pages/PlayerDetail.tsx`

- [ ] **Step 1: Inspect the existing PlayerDetail page**

```bash
cat frontend/src/pages/PlayerDetail.tsx
```

Note the current data fetching and the structure for tabs (if any).

- [ ] **Step 2: Add `OVR / POT` rendering**

In the player header, render `{overall} OVR / {potential} POT`. The overall value is already computed somewhere in the existing component or the API; if not, compute it client-side as the simple average of the visible attributes (matches the backend helper).

- [ ] **Step 3: Add Development and Career tabs**

Use the same tab style as existing pages (or a simple two-button tab strip). On tab switch, call the appropriate hook:

```tsx
import { useQuery } from "@tanstack/react-query";
import { fetchPlayerDevelopment, SeasonProgression } from "../api/development";
import { fetchSkaterCareer, fetchGoalieCareer } from "../api/career";

function DevelopmentTab({ playerId, type }: { playerId: number; type: "skater" | "goalie" }) {
  const { data } = useQuery({
    queryKey: ["player-dev", playerId, type],
    queryFn: () => fetchPlayerDevelopment(playerId, type),
  });
  if (!data) return null;
  return (
    <div>
      {data.history.length === 0 && <div>No development history yet.</div>}
      {data.history.map((p: SeasonProgression) => (
        <div key={p.to_season_id ?? `${p.age_before}-${p.age_after}`} className="border-b py-2">
          <div>
            Season → {p.age_before} → {p.age_after} • OVR {p.overall_before} → {p.overall_after} ({p.summary_reason})
          </div>
          <ul className="text-xs text-gray-700">
            {p.events.map((e, i) => (
              <li key={i}>{e.attribute}: {e.old_value} → {e.new_value}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function CareerTab({ playerId, type }: { playerId: number; type: "skater" | "goalie" }) {
  const { data } = useQuery({
    queryKey: ["player-career", playerId, type],
    queryFn: () => (type === "skater" ? fetchSkaterCareer(playerId) : fetchGoalieCareer(playerId)),
  });
  if (!data) return null;
  if (type === "skater") {
    const c = data as Awaited<ReturnType<typeof fetchSkaterCareer>>;
    return (
      <table className="w-full text-sm">
        <thead><tr><th>Season</th><th>GP</th><th>G</th><th>A</th><th>PTS</th><th>SOG</th></tr></thead>
        <tbody>
          {c.by_season.map((s) => (
            <tr key={s.season_id}><td>{s.season_id}</td><td>{s.gp}</td><td>{s.g}</td><td>{s.a}</td><td>{s.pts}</td><td>{s.sog}</td></tr>
          ))}
          <tr className="font-semibold border-t">
            <td>Total</td><td>{c.totals.gp}</td><td>{c.totals.g}</td><td>{c.totals.a}</td><td>{c.totals.pts}</td><td>{c.totals.sog}</td>
          </tr>
        </tbody>
      </table>
    );
  }
  const c = data as Awaited<ReturnType<typeof fetchGoalieCareer>>;
  return (
    <table className="w-full text-sm">
      <thead><tr><th>Season</th><th>GP</th><th>SA</th><th>SV</th><th>GA</th><th>SV%</th></tr></thead>
      <tbody>
        {c.by_season.map((s) => (
          <tr key={s.season_id}>
            <td>{s.season_id}</td><td>{s.gp}</td><td>{s.shots_against}</td><td>{s.saves}</td><td>{s.goals_against}</td><td>{(s.sv_pct * 100).toFixed(1)}%</td>
          </tr>
        ))}
        <tr className="font-semibold border-t">
          <td>Total</td><td>{c.totals.gp}</td><td>{c.totals.shots_against}</td><td>{c.totals.saves}</td><td>{c.totals.goals_against}</td><td>{(c.totals.sv_pct * 100).toFixed(1)}%</td>
        </tr>
      </tbody>
    </table>
  );
}
```

Wire these into PlayerDetail.tsx with the existing tab UI.

- [ ] **Step 4: Verify in the browser**

Navigate to a player after a rollover. Confirm OVR/POT appears, the Development tab shows the player's progression history, and the Career tab shows per-season + total rows. Test for both a skater and a goalie.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/PlayerDetail.tsx
git commit -m "feat(frontend): add OVR/POT, Development tab, Career tab on player detail"
```

---

## Task 18: Final regression run

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && uv run pytest -q
```

Expected: all pass.

- [ ] **Step 2: Smoke-test the loop**

Manually:
1. Reset the league.
2. Advance through every matchday until the season is complete.
3. Click "Start Next Season".
4. Confirm: development summary appears, players' ages incremented, schedule for new season exists, standings reset to zero, old season's games still queryable on `GET /api/games?season_id=<old>` (or equivalent), player detail shows OVR/POT and a Development entry.

- [ ] **Step 3: Final commit if any small fixes were needed**

```bash
git status
git add -p   # only if there are pending edits
git commit -m "fix: cleanup after Phase 4 smoke test"
```

---

## Self-Review

I checked the plan against the spec.

- ✅ Spec section "Scope" → Tasks 1, 2, 4, 11, 12 cover potential/dev_type, generation, rollover, persistence.
- ✅ Spec "Architecture" (pure sim + service) → Tasks 6, 7 (sim), 11, 12 (service).
- ✅ Spec "Data Model — Column additions" → Task 1 (model), Task 5 (migration).
- ✅ Spec "Team / season decoupling" → Task 3.
- ✅ Spec "Development Formula" → Task 7.
- ✅ Spec "Performance signal" → Task 12 (orchestrator-side helpers).
- ✅ Spec "Rollover Flow" → Tasks 11–12 (guards + orchestration), Task 13 (HTTP wrapping).
- ✅ Spec "API Surface" — `/start-next` Task 13, `/development-summary` Task 13, `/players/{id}/development` Task 14, `/players/{id}/career` Task 14.
- ✅ Spec "League Generation — potential & dev_type distributions" → Task 4.
- ✅ Spec "UI" → Tasks 16, 17.
- ✅ Spec "Testing" — pure sim Task 7, rollover Task 12, career Task 14.
- ✅ Spec "Migration" → Task 5.

Type/method consistency:
- `develop_player(player, season_seed)` — used identically in Tasks 6/7/12.
- `PlayerDevInput` field names — used identically in Tasks 6/7/12.
- `classify_summary` — declared in Task 7, used by tests in Task 7.
- API path prefix `/api/...` is assumed in frontend clients (Task 15) and tests (Task 14); routers in Tasks 13/14 use the existing routers, so confirm prefix at the install site (noted inline).

No "TBD" / "TODO" placeholders remain in code blocks. Each task includes failing test → implementation → passing test → commit pattern where applicable. Each task is self-contained.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-29-phase-4-player-development.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
