# Free Agent Pool (P1.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a vertical slice of free agency: seeded FA pool at league creation, list/filter/sort endpoints, sign + release endpoints gated to the user team, `/free-agents` page, and a release button on the user's team page.

**Architecture:** `team_id` on `skater`/`goalie` becomes nullable; `team_id IS NULL` ⇔ free agent. Generation reuses the existing player generator under `app/services/generation/`. Service layer enforces user-team gating using the existing `Season.user_team_id` and `NotUserTeam` patterns from `gameplan_service`. Lineup FKs become nullable so release can clear slot references without dropping the lineup row.

**Tech Stack:** FastAPI, SQLAlchemy 2.x typed mappings, Alembic, Pydantic, pytest, React + TanStack Query + TanStack Router (file-based routes), TypeScript, Tailwind.

**Spec:** `docs/superpowers/specs/2026-05-03-free-agent-pool-design.md`

---

## File Map

**Backend — create:**
- `backend/alembic/versions/e5f6a7b8c9d0_phase6_free_agency.py`
- `backend/app/services/generation/free_agents.py`
- `backend/app/services/free_agents_service.py`
- `backend/app/schemas/free_agents.py`
- `backend/app/api/free_agents.py`
- `backend/tests/test_free_agent_generation.py`
- `backend/tests/test_free_agents_api.py`
- `backend/tests/test_sign_release_api.py`

**Backend — modify:**
- `backend/app/models/skater.py` (team_id → `int | None`)
- `backend/app/models/goalie.py` (team_id → `int | None`)
- `backend/app/models/lineup.py` (all skater/goalie FK columns → `int | None`)
- `backend/app/services/generation/players.py` (export `skater_overall`, `goalie_overall`)
- `backend/app/services/league_service.py` (call FA generator)
- `backend/app/api/__init__.py` (register `free_agents` router)

**Frontend — create:**
- `frontend/src/queries/free-agents.ts`
- `frontend/src/routes/free-agents.tsx`

**Frontend — modify:**
- `frontend/src/api/types.ts` (add FA types)
- `frontend/src/components/Shell.tsx` (add "Free Agents" nav entry)
- `frontend/src/routes/team.$teamId.tsx` (add Release button on user team rows)

**Docs — modify:**
- `docs/product-scope.md`
- `docs/not-now.md`
- `docs/phase-6.md` (new)

---

## Conventions

- Run backend tests from `backend/`: `cd backend && pytest <path>::<name> -v`.
- Run frontend type check from `frontend/`: `cd frontend && npm run typecheck` (or `tsc --noEmit`).
- Each task ends with a commit using a `feat:` / `fix:` / `chore:` / `docs:` prefix and a short imperative summary.
- The plan assumes the engineer is unfamiliar with the codebase. Code blocks show the actual content to write — copy/paste, don't paraphrase.

---

## Task 1: Alembic migration — nullable team_id and lineup FKs

**Files:**
- Create: `backend/alembic/versions/e5f6a7b8c9d0_phase6_free_agency.py`

- [ ] **Step 1: Confirm latest migration revision**

Run: `cd backend && ls alembic/versions/`
Expected: latest is `d4e5f6a7b8c9_phase5a_team_gameplan.py`. Use `d4e5f6a7b8c9` as `down_revision`.

- [ ] **Step 2: Write migration file**

Create `backend/alembic/versions/e5f6a7b8c9d0_phase6_free_agency.py`:

```python
"""phase 6: free agency (nullable team_id, nullable lineup FKs)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SKATER_LINEUP_COLS = [
    "line1_lw_id", "line1_c_id", "line1_rw_id",
    "line2_lw_id", "line2_c_id", "line2_rw_id",
    "line3_lw_id", "line3_c_id", "line3_rw_id",
    "line4_lw_id", "line4_c_id", "line4_rw_id",
    "pair1_ld_id", "pair1_rd_id",
    "pair2_ld_id", "pair2_rd_id",
    "pair3_ld_id", "pair3_rd_id",
]
GOALIE_LINEUP_COLS = ["starting_goalie_id", "backup_goalie_id"]


def upgrade() -> None:
    # skater.team_id: NOT NULL -> NULLABLE, CASCADE -> SET NULL
    with op.batch_alter_table("skater") as batch:
        batch.alter_column("team_id", nullable=True)
        batch.drop_constraint("skater_team_id_fkey", type_="foreignkey")
        batch.create_foreign_key(
            "skater_team_id_fkey", "team", ["team_id"], ["id"], ondelete="SET NULL"
        )
    with op.batch_alter_table("goalie") as batch:
        batch.alter_column("team_id", nullable=True)
        batch.drop_constraint("goalie_team_id_fkey", type_="foreignkey")
        batch.create_foreign_key(
            "goalie_team_id_fkey", "team", ["team_id"], ["id"], ondelete="SET NULL"
        )
    # lineup: every skater/goalie slot becomes nullable so release can clear it.
    with op.batch_alter_table("lineup") as batch:
        for col in SKATER_LINEUP_COLS + GOALIE_LINEUP_COLS:
            batch.alter_column(col, nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("lineup") as batch:
        for col in SKATER_LINEUP_COLS + GOALIE_LINEUP_COLS:
            batch.alter_column(col, nullable=False)
    with op.batch_alter_table("goalie") as batch:
        batch.drop_constraint("goalie_team_id_fkey", type_="foreignkey")
        batch.create_foreign_key(
            "goalie_team_id_fkey", "team", ["team_id"], ["id"], ondelete="CASCADE"
        )
        batch.alter_column("team_id", nullable=False)
    with op.batch_alter_table("skater") as batch:
        batch.drop_constraint("skater_team_id_fkey", type_="foreignkey")
        batch.create_foreign_key(
            "skater_team_id_fkey", "team", ["team_id"], ["id"], ondelete="CASCADE"
        )
        batch.alter_column("team_id", nullable=False)
```

> Note: SQLAlchemy's autogenerated FK names follow `<table>_<col>_fkey` for Postgres. If `alembic upgrade head` reports a different constraint name (e.g., `fk_skater_team_id_team`), inspect with `\d skater` in psql, update the constants in this migration, and rerun.

- [ ] **Step 3: Apply migration locally**

Run: `cd backend && alembic upgrade head`
Expected: no error; `alembic current` shows `e5f6a7b8c9d0 (head)`.

- [ ] **Step 4: Verify schema (Postgres)**

Run: `cd backend && psql $DATABASE_URL -c "\d skater" | grep team_id`
Expected: line shows `team_id | integer |` with no `not null`.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/e5f6a7b8c9d0_phase6_free_agency.py
git commit -m "feat(db): phase6 migration — nullable team_id, nullable lineup FKs"
```

---

## Task 2: Update SQLAlchemy models for nullability

**Files:**
- Modify: `backend/app/models/skater.py`
- Modify: `backend/app/models/goalie.py`
- Modify: `backend/app/models/lineup.py`

- [ ] **Step 1: Update Skater model**

Edit `backend/app/models/skater.py`, replace the `team_id` line:

```python
team_id: Mapped[int | None] = mapped_column(
    ForeignKey("team.id", ondelete="SET NULL"), index=True, nullable=True
)
```

- [ ] **Step 2: Update Goalie model**

Edit `backend/app/models/goalie.py`, replace the `team_id` line:

```python
team_id: Mapped[int | None] = mapped_column(
    ForeignKey("team.id", ondelete="SET NULL"), index=True, nullable=True
)
```

- [ ] **Step 3: Update Lineup model**

Edit `backend/app/models/lineup.py`. For every skater/goalie FK column, change `Mapped[int]` to `Mapped[int | None]` and add `nullable=True` to `mapped_column`. Example for one column:

```python
line1_lw_id: Mapped[int | None] = mapped_column(ForeignKey("skater.id"), nullable=True)
```

Apply the same change to all 18 skater FK columns and both goalie FK columns. Leave `id` and `team_id` unchanged (team_id stays NOT NULL on lineup).

- [ ] **Step 4: Run smoke test**

Run: `cd backend && pytest tests/test_models_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend suite to confirm nothing regressed**

Run: `cd backend && pytest -x`
Expected: PASS. Some tests may exercise lineup creation — those should still pass since the columns are still populated by the lineup generator.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/skater.py backend/app/models/goalie.py backend/app/models/lineup.py
git commit -m "feat(models): allow null team_id and null lineup slot FKs"
```

---

## Task 3: Expose OVR helpers from the player generator

The schemas need OVR computed at serialization time. Today, `_skater_overall` and `_goalie_overall` are private to `players.py`. Promote them.

**Files:**
- Modify: `backend/app/services/generation/players.py`

- [ ] **Step 1: Rename private helpers to public**

Edit `backend/app/services/generation/players.py`:

- Rename `_skater_overall` → `skater_overall` (drop underscore).
- Rename `_goalie_overall` → `goalie_overall`.
- Update internal call sites in the same file.

- [ ] **Step 2: Run tests**

Run: `cd backend && pytest -x`
Expected: PASS. (No external callers exist today.)

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/generation/players.py
git commit -m "refactor(gen): expose skater_overall/goalie_overall as public helpers"
```

---

## Task 4: Free-agent generator (with tests)

**Files:**
- Create: `backend/app/services/generation/free_agents.py`
- Create: `backend/tests/test_free_agent_generation.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_free_agent_generation.py`:

```python
import random
from collections import Counter

from app.models import Goalie, Skater
from app.services.generation.free_agents import generate_free_agent_pool


def test_generates_expected_counts(db_session):
    rng = random.Random(42)
    used_names: set[str] = set()
    generate_free_agent_pool(rng, db_session, used_names)
    db_session.flush()

    skaters = db_session.query(Skater).filter(Skater.team_id.is_(None)).all()
    goalies = db_session.query(Goalie).filter(Goalie.team_id.is_(None)).all()
    assert len(skaters) == 40
    assert len(goalies) == 5


def test_position_distribution(db_session):
    rng = random.Random(42)
    generate_free_agent_pool(rng, db_session, set())
    db_session.flush()
    counts = Counter(
        s.position for s in db_session.query(Skater).filter(Skater.team_id.is_(None)).all()
    )
    assert counts == {"LW": 8, "C": 8, "RW": 8, "LD": 8, "RD": 8}


def test_pool_is_deterministic(db_session_factory):
    db1 = db_session_factory()
    generate_free_agent_pool(random.Random(99), db1, set())
    db1.flush()
    snap1 = sorted(
        (s.name, s.position, s.skating, s.shooting, s.passing, s.defense, s.physical)
        for s in db1.query(Skater).filter(Skater.team_id.is_(None)).all()
    )
    db1.close()

    db2 = db_session_factory()
    generate_free_agent_pool(random.Random(99), db2, set())
    db2.flush()
    snap2 = sorted(
        (s.name, s.position, s.skating, s.shooting, s.passing, s.defense, s.physical)
        for s in db2.query(Skater).filter(Skater.team_id.is_(None)).all()
    )
    db2.close()
    assert snap1 == snap2


def test_pool_includes_a_gem(db_session):
    from app.services.generation.players import skater_overall
    rng = random.Random(7)
    generate_free_agent_pool(rng, db_session, set())
    db_session.flush()
    skaters = db_session.query(Skater).filter(Skater.team_id.is_(None)).all()
    overalls = [
        skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)
        for s in skaters
    ]
    assert max(overalls) >= 75


def test_no_name_collision_with_used(db_session):
    used = {"Alice Free", "Bob Pool"}
    rng = random.Random(5)
    generate_free_agent_pool(rng, db_session, used)
    db_session.flush()
    names = {s.name for s in db_session.query(Skater).filter(Skater.team_id.is_(None)).all()}
    names |= {g.name for g in db_session.query(Goalie).filter(Goalie.team_id.is_(None)).all()}
    assert names.isdisjoint(used)
```

> If `db_session` / `db_session_factory` fixtures don't exist with these exact names, inspect `backend/tests/conftest.py` and adapt the fixture names to match. Use whatever per-test in-memory session fixture the suite already provides.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_free_agent_generation.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.generation.free_agents`.

- [ ] **Step 3: Implement the generator**

Create `backend/app/services/generation/free_agents.py`:

```python
import random

from sqlalchemy.orm import Session

from app.models import Goalie, Skater
from app.services.generation.names import make_player_name
from app.services.generation.players import (
    DEV_TYPE_WEIGHTS,
    _pick_dev_type,
    _potential_for,
    goalie_overall,
    skater_overall,
)

FA_SKATER_LAYOUT = ["LW"] * 8 + ["C"] * 8 + ["RW"] * 8 + ["LD"] * 8 + ["RD"] * 8
FA_GOALIE_COUNT = 5
FA_SKATER_GEMS = 2
FA_GOALIE_GEMS = 1


def _fa_attr(rng: random.Random) -> int:
    return max(40, min(88, int(rng.gauss(63, 7))))


def _fa_goalie_attr(rng: random.Random) -> int:
    return max(45, min(88, int(rng.gauss(68, 6))))


def _bump(value: int, delta: int) -> int:
    return max(40, min(95, value + delta))


def generate_free_agent_pool(
    rng: random.Random, db: Session, used_names: set[str]
) -> None:
    """Generate the league's initial free-agent pool. Called once during
    league creation, after rostered players. Players have team_id=None."""
    skaters: list[Skater] = []
    for pos in FA_SKATER_LAYOUT:
        skating = _fa_attr(rng)
        shooting = _fa_attr(rng)
        passing = _fa_attr(rng)
        defense = _fa_attr(rng) if pos in ("LD", "RD") else max(40, _fa_attr(rng) - 5)
        physical = _fa_attr(rng)
        age = rng.randint(19, 35)
        overall = skater_overall(skating, shooting, passing, defense, physical)
        sk = Skater(
            team_id=None,
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
        db.add(sk)
        skaters.append(sk)

    goalies: list[Goalie] = []
    for _ in range(FA_GOALIE_COUNT):
        reflexes = _fa_goalie_attr(rng)
        positioning = _fa_goalie_attr(rng)
        rebound_control = _fa_goalie_attr(rng)
        puck_handling = _fa_goalie_attr(rng)
        mental = _fa_goalie_attr(rng)
        age = rng.randint(20, 36)
        overall = goalie_overall(reflexes, positioning, rebound_control, puck_handling, mental)
        g = Goalie(
            team_id=None,
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
        db.add(g)
        goalies.append(g)

    # Gem injection: randomly bump a couple of skaters and one goalie so the
    # pool isn't uniformly mediocre.
    for sk in rng.sample(skaters, FA_SKATER_GEMS):
        delta = rng.randint(8, 14)
        sk.skating = _bump(sk.skating, delta)
        sk.shooting = _bump(sk.shooting, delta)
        sk.passing = _bump(sk.passing, delta)
        sk.defense = _bump(sk.defense, delta)
        sk.physical = _bump(sk.physical, delta)
        sk.potential = _potential_for(
            rng,
            sk.age,
            skater_overall(sk.skating, sk.shooting, sk.passing, sk.defense, sk.physical),
        )

    for g in rng.sample(goalies, FA_GOALIE_GEMS):
        delta = rng.randint(8, 14)
        g.reflexes = _bump(g.reflexes, delta)
        g.positioning = _bump(g.positioning, delta)
        g.rebound_control = _bump(g.rebound_control, delta)
        g.puck_handling = _bump(g.puck_handling, delta)
        g.mental = _bump(g.mental, delta)
        g.potential = _potential_for(
            rng,
            g.age,
            goalie_overall(g.reflexes, g.positioning, g.rebound_control, g.puck_handling, g.mental),
        )
```

> `_pick_dev_type` and `_potential_for` are still private to `players.py`. They're being imported across modules in the same `generation/` package, which is acceptable — they're internal to the generation layer. If you prefer, drop the underscore from both in `players.py` first (do it as a tiny inline rename; no separate task) and update the import here.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_free_agent_generation.py -v`
Expected: all 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/generation/free_agents.py backend/tests/test_free_agent_generation.py
git commit -m "feat(gen): seeded free-agent pool generator"
```

---

## Task 5: Wire FA generation into league creation

**Files:**
- Modify: `backend/app/services/league_service.py`

- [ ] **Step 1: Update `create_or_reset_league`**

Edit `backend/app/services/league_service.py`. Add the import:

```python
from app.services.generation.free_agents import generate_free_agent_pool
```

Inside `create_or_reset_league`, after `generate_teams(...)` runs but before `generate_default_lineups`, add:

```python
    # Seed the league's free-agent pool. Shares used_names with rostered players.
    used_names: set[str] = {p.name for p in db.query(Skater).all()}
    used_names |= {g.name for g in db.query(Goalie).all()}
    generate_free_agent_pool(rng, db, used_names)
    db.flush()
```

> `generate_teams` returns the team list but doesn't expose its `used_names` set. Reconstructing the set from the DB is simpler than threading it through the API. The query is cheap (4 teams × 22 players).

- [ ] **Step 2: Add a smoke test that league creation produces FAs**

Edit `backend/tests/test_models_smoke.py` (or add a new `test_league_creates_free_agents.py` — pick whatever matches the project's existing test style):

```python
def test_league_creation_seeds_free_agent_pool(client):
    r = client.post("/api/league", json={"seed": 42})
    assert r.status_code == 200

    from app.models import Skater, Goalie
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        fa_skaters = db.query(Skater).filter(Skater.team_id.is_(None)).count()
        fa_goalies = db.query(Goalie).filter(Goalie.team_id.is_(None)).count()
    finally:
        db.close()
    assert fa_skaters == 40
    assert fa_goalies == 5
```

> Adjust the league-creation endpoint path and payload shape to match what `app/api/league.py` actually accepts.

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest -x`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/league_service.py backend/tests/
git commit -m "feat(league): seed free-agent pool at league creation"
```

---

## Task 6: Pydantic schemas for FA listing

**Files:**
- Create: `backend/app/schemas/free_agents.py`

- [ ] **Step 1: Write the schemas**

Create `backend/app/schemas/free_agents.py`:

```python
from pydantic import BaseModel, ConfigDict, computed_field

from app.services.generation.players import goalie_overall, skater_overall


class FreeAgentSkaterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    position: str
    potential: int
    development_type: str
    skating: int
    shooting: int
    passing: int
    defense: int
    physical: int

    @computed_field  # type: ignore[misc]
    @property
    def ovr(self) -> int:
        return skater_overall(
            self.skating, self.shooting, self.passing, self.defense, self.physical
        )


class FreeAgentGoalieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    potential: int
    development_type: str
    reflexes: int
    positioning: int
    rebound_control: int
    puck_handling: int
    mental: int

    @computed_field  # type: ignore[misc]
    @property
    def ovr(self) -> int:
        return goalie_overall(
            self.reflexes,
            self.positioning,
            self.rebound_control,
            self.puck_handling,
            self.mental,
        )


class SignReleaseSkaterOut(FreeAgentSkaterOut):
    team_id: int | None


class SignReleaseGoalieOut(FreeAgentGoalieOut):
    team_id: int | None
```

- [ ] **Step 2: Verify the file imports cleanly**

Run: `cd backend && python -c "from app.schemas.free_agents import FreeAgentSkaterOut, FreeAgentGoalieOut, SignReleaseSkaterOut, SignReleaseGoalieOut"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/free_agents.py
git commit -m "feat(schemas): free-agent list/sign/release output models"
```

---

## Task 7: FA service — list functions

**Files:**
- Create: `backend/app/services/free_agents_service.py`

- [ ] **Step 1: Implement list helpers**

Create `backend/app/services/free_agents_service.py`:

```python
from typing import Literal

from sqlalchemy.orm import Session

from app.models import Goalie, Season, Skater, Team
from app.errors import (
    GoalieNotFound,
    NotUserTeam,
    SkaterNotFound,
    TeamNotFound,
)


SkaterSort = Literal["ovr", "potential", "age", "position"]
GoalieSort = Literal["ovr", "potential", "age"]
Order = Literal["asc", "desc"]


def _current_user_team_id(db: Session) -> int | None:
    season = db.query(Season).order_by(Season.id.desc()).first()
    return season.user_team_id if season else None


def _skater_ovr_expr() -> object:
    # Used for SQL-side sorting so we don't materialize the whole pool first.
    return (Skater.skating + Skater.shooting + Skater.passing + Skater.defense + Skater.physical) / 5.0


def _goalie_ovr_expr() -> object:
    return (
        Goalie.reflexes + Goalie.positioning + Goalie.rebound_control
        + Goalie.puck_handling + Goalie.mental
    ) / 5.0


def list_free_agent_skaters(
    db: Session,
    *,
    position: str | None = None,
    min_ovr: int | None = None,
    min_potential: int | None = None,
    max_age: int | None = None,
    sort: SkaterSort = "ovr",
    order: Order = "desc",
) -> list[Skater]:
    q = db.query(Skater).filter(Skater.team_id.is_(None))
    if position:
        q = q.filter(Skater.position == position)
    if min_potential is not None:
        q = q.filter(Skater.potential >= min_potential)
    if max_age is not None:
        q = q.filter(Skater.age <= max_age)
    if min_ovr is not None:
        q = q.filter(_skater_ovr_expr() >= min_ovr)

    sort_map = {
        "ovr": _skater_ovr_expr(),
        "potential": Skater.potential,
        "age": Skater.age,
        "position": Skater.position,
    }
    col = sort_map[sort]
    q = q.order_by(col.asc() if order == "asc" else col.desc())
    return q.all()


def list_free_agent_goalies(
    db: Session,
    *,
    min_ovr: int | None = None,
    min_potential: int | None = None,
    max_age: int | None = None,
    sort: GoalieSort = "ovr",
    order: Order = "desc",
) -> list[Goalie]:
    q = db.query(Goalie).filter(Goalie.team_id.is_(None))
    if min_potential is not None:
        q = q.filter(Goalie.potential >= min_potential)
    if max_age is not None:
        q = q.filter(Goalie.age <= max_age)
    if min_ovr is not None:
        q = q.filter(_goalie_ovr_expr() >= min_ovr)

    sort_map = {
        "ovr": _goalie_ovr_expr(),
        "potential": Goalie.potential,
        "age": Goalie.age,
    }
    col = sort_map[sort]
    q = q.order_by(col.asc() if order == "asc" else col.desc())
    return q.all()
```

- [ ] **Step 2: Smoke test the list functions**

Run: `cd backend && python -c "from app.services.free_agents_service import list_free_agent_skaters, list_free_agent_goalies"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/free_agents_service.py
git commit -m "feat(svc): free-agent list functions with filter/sort"
```

---

## Task 8: FA service — sign function (with tests)

**Files:**
- Modify: `backend/app/services/free_agents_service.py`
- Create: `backend/tests/test_sign_release_api.py` (we'll grow this in Tasks 8 and 9)

- [ ] **Step 1: Write failing tests for sign behavior**

Create `backend/tests/test_sign_release_api.py`:

```python
import pytest

from app.models import Skater, Goalie


def _create_league(client, seed=42):
    r = client.post("/api/league", json={"seed": seed})
    assert r.status_code == 200
    return r.json()


def _user_team_id(client) -> int:
    return client.get("/api/league").json()["user_team_id"]


def _any_fa_skater(db) -> Skater:
    return db.query(Skater).filter(Skater.team_id.is_(None)).first()


def test_sign_skater_attaches_to_user_team(client, db_session):
    _create_league(client)
    team_id = _user_team_id(client)
    sk = _any_fa_skater(db_session)
    r = client.post(f"/api/teams/{team_id}/sign/skater/{sk.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["team_id"] == team_id
    db_session.expire_all()
    assert db_session.get(Skater, sk.id).team_id == team_id


def test_sign_rejected_for_non_user_team(client, db_session):
    _create_league(client)
    user_id = _user_team_id(client)
    other_id = next(
        t["id"] for t in client.get("/api/teams").json() if t["id"] != user_id
    )
    sk = _any_fa_skater(db_session)
    r = client.post(f"/api/teams/{other_id}/sign/skater/{sk.id}")
    assert r.status_code == 403
    assert r.json()["error_code"] == "NotUserTeam"


def test_sign_rejected_when_already_signed(client, db_session):
    _create_league(client)
    team_id = _user_team_id(client)
    rostered = (
        db_session.query(Skater).filter(Skater.team_id.is_not(None)).first()
    )
    r = client.post(f"/api/teams/{team_id}/sign/skater/{rostered.id}")
    assert r.status_code == 400
```

> Adjust fixture names (`client`, `db_session`) and the teams-list endpoint to match the project's conftest.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_sign_release_api.py -v`
Expected: FAIL — endpoint doesn't exist yet (404 or import error).

- [ ] **Step 3: Implement `sign_skater` and `sign_goalie`**

Append to `backend/app/services/free_agents_service.py`:

```python
from app.errors import DomainError


class PlayerNotFreeAgent(DomainError):
    code = "PlayerNotFreeAgent"
    status = 400


def _ensure_user_team(db: Session, team_id: int) -> Team:
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise TeamNotFound(f"team {team_id} not found")
    if _current_user_team_id(db) != team_id:
        raise NotUserTeam(f"team {team_id} is not the user team")
    return team


def sign_skater(db: Session, team_id: int, skater_id: int) -> Skater:
    _ensure_user_team(db, team_id)
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    if sk.team_id is not None:
        raise PlayerNotFreeAgent(f"skater {skater_id} is already on a team")
    sk.team_id = team_id
    db.flush()
    return sk


def sign_goalie(db: Session, team_id: int, goalie_id: int) -> Goalie:
    _ensure_user_team(db, team_id)
    g = db.query(Goalie).filter_by(id=goalie_id).first()
    if not g:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    if g.team_id is not None:
        raise PlayerNotFreeAgent(f"goalie {goalie_id} is already on a team")
    g.team_id = team_id
    db.flush()
    return g
```

> Add `PlayerNotFreeAgent` to `app/errors.py` instead of defining it inline if your codebase prefers all error classes centralized. Pick one location consistently with how `gameplan_service` handles its errors.

- [ ] **Step 4: Add the API stubs needed for the tests to reach the service**

(We're going to wire endpoints fully in Task 10, but the tests need them now. If you prefer, defer the test runs from Task 8/9 until after Task 10 — pick one approach, document it in the commit.)

To keep TDD honest, wire just enough route to make Task 8 tests pass: append to `backend/app/api/__init__.py` after the next task creates `app/api/free_agents.py`. **Do this work as part of Task 10.** For now, mark these tests `pytest.mark.xfail(reason="endpoints land in Task 10")` or move them into Task 10. Pick one and be consistent.

- [ ] **Step 5: Commit (service only)**

```bash
git add backend/app/services/free_agents_service.py
git commit -m "feat(svc): sign_skater and sign_goalie with user-team gate"
```

---

## Task 9: FA service — release function (with lineup-slot nulling)

**Files:**
- Modify: `backend/app/services/free_agents_service.py`

- [ ] **Step 1: Implement `release_skater` and `release_goalie`**

Append to `backend/app/services/free_agents_service.py`:

```python
from app.models import Lineup

SKATER_LINEUP_COLS = (
    "line1_lw_id", "line1_c_id", "line1_rw_id",
    "line2_lw_id", "line2_c_id", "line2_rw_id",
    "line3_lw_id", "line3_c_id", "line3_rw_id",
    "line4_lw_id", "line4_c_id", "line4_rw_id",
    "pair1_ld_id", "pair1_rd_id",
    "pair2_ld_id", "pair2_rd_id",
    "pair3_ld_id", "pair3_rd_id",
)
GOALIE_LINEUP_COLS = ("starting_goalie_id", "backup_goalie_id")


class PlayerNotOnTeam(DomainError):
    code = "PlayerNotOnTeam"
    status = 400


def _clear_skater_from_lineup(db: Session, team_id: int, skater_id: int) -> None:
    lu = db.query(Lineup).filter_by(team_id=team_id).first()
    if not lu:
        return
    for col in SKATER_LINEUP_COLS:
        if getattr(lu, col) == skater_id:
            setattr(lu, col, None)


def _clear_goalie_from_lineup(db: Session, team_id: int, goalie_id: int) -> None:
    lu = db.query(Lineup).filter_by(team_id=team_id).first()
    if not lu:
        return
    for col in GOALIE_LINEUP_COLS:
        if getattr(lu, col) == goalie_id:
            setattr(lu, col, None)


def release_skater(db: Session, team_id: int, skater_id: int) -> Skater:
    _ensure_user_team(db, team_id)
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    if sk.team_id != team_id:
        raise PlayerNotOnTeam(f"skater {skater_id} is not on team {team_id}")
    _clear_skater_from_lineup(db, team_id, skater_id)
    sk.team_id = None
    db.flush()
    return sk


def release_goalie(db: Session, team_id: int, goalie_id: int) -> Goalie:
    _ensure_user_team(db, team_id)
    g = db.query(Goalie).filter_by(id=goalie_id).first()
    if not g:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    if g.team_id != team_id:
        raise PlayerNotOnTeam(f"goalie {goalie_id} is not on team {team_id}")
    _clear_goalie_from_lineup(db, team_id, goalie_id)
    g.team_id = None
    db.flush()
    return g
```

- [ ] **Step 2: Add release tests**

Append to `backend/tests/test_sign_release_api.py`:

```python
def test_release_clears_lineup_slots(client, db_session):
    _create_league(client)
    team_id = _user_team_id(client)
    lu = client.get(f"/api/teams/{team_id}/lineup").json()
    skater_id = lu["line1_c_id"]

    r = client.post(f"/api/teams/{team_id}/release/skater/{skater_id}")
    assert r.status_code == 200
    assert r.json()["team_id"] is None

    after = client.get(f"/api/teams/{team_id}/lineup").json()
    assert after["line1_c_id"] is None

    db_session.expire_all()
    assert db_session.get(Skater, skater_id).team_id is None


def test_release_rejected_for_non_user_team(client, db_session):
    _create_league(client)
    user_id = _user_team_id(client)
    other_id = next(
        t["id"] for t in client.get("/api/teams").json() if t["id"] != user_id
    )
    other_skater = (
        db_session.query(Skater).filter(Skater.team_id == other_id).first()
    )
    r = client.post(f"/api/teams/{user_id}/release/skater/{other_skater.id}")
    assert r.status_code == 400  # not on user's team


def test_release_then_resign_keeps_id(client, db_session):
    _create_league(client)
    team_id = _user_team_id(client)
    sk_id = client.get(f"/api/teams/{team_id}/lineup").json()["line2_lw_id"]
    client.post(f"/api/teams/{team_id}/release/skater/{sk_id}")
    r = client.post(f"/api/teams/{team_id}/sign/skater/{sk_id}")
    assert r.status_code == 200
    assert r.json()["id"] == sk_id
    assert r.json()["team_id"] == team_id
```

- [ ] **Step 3: Commit (service + tests)**

```bash
git add backend/app/services/free_agents_service.py backend/tests/test_sign_release_api.py
git commit -m "feat(svc): release_skater/release_goalie with lineup-slot clearing"
```

---

## Task 10: FA API endpoints

**Files:**
- Create: `backend/app/api/free_agents.py`
- Modify: `backend/app/api/__init__.py`
- Create: `backend/tests/test_free_agents_api.py`

- [ ] **Step 1: Write list-endpoint tests**

Create `backend/tests/test_free_agents_api.py`:

```python
def _create_league(client):
    assert client.post("/api/league", json={"seed": 42}).status_code == 200


def test_list_skaters_returns_only_free_agents(client):
    _create_league(client)
    rows = client.get("/api/free-agents/skaters").json()
    assert len(rows) >= 40
    assert all(r.get("team_id", None) is None or "team_id" not in r for r in rows)


def test_list_skaters_filter_by_position(client):
    _create_league(client)
    rows = client.get("/api/free-agents/skaters?position=C").json()
    assert all(r["position"] == "C" for r in rows)
    assert len(rows) >= 8


def test_list_skaters_min_ovr(client):
    _create_league(client)
    rows = client.get("/api/free-agents/skaters?min_ovr=70").json()
    assert all(r["ovr"] >= 70 for r in rows)


def test_list_skaters_sort_age_asc(client):
    _create_league(client)
    rows = client.get("/api/free-agents/skaters?sort=age&order=asc").json()
    ages = [r["age"] for r in rows]
    assert ages == sorted(ages)


def test_list_goalies(client):
    _create_league(client)
    rows = client.get("/api/free-agents/goalies").json()
    assert len(rows) >= 5
    assert all("ovr" in r for r in rows)
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `cd backend && pytest tests/test_free_agents_api.py -v`
Expected: FAIL with 404 (route not registered).

- [ ] **Step 3: Implement the API module**

Create `backend/app/api/free_agents.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.free_agents import (
    FreeAgentGoalieOut,
    FreeAgentSkaterOut,
    SignReleaseGoalieOut,
    SignReleaseSkaterOut,
)
from app.services import free_agents_service as svc

router = APIRouter(tags=["free-agents"])


@router.get("/free-agents/skaters", response_model=list[FreeAgentSkaterOut])
def list_skaters(
    position: str | None = Query(default=None),
    min_ovr: int | None = Query(default=None),
    min_potential: int | None = Query(default=None),
    max_age: int | None = Query(default=None),
    sort: str = Query(default="ovr"),
    order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    return svc.list_free_agent_skaters(
        db,
        position=position,
        min_ovr=min_ovr,
        min_potential=min_potential,
        max_age=max_age,
        sort=sort,  # type: ignore[arg-type]
        order=order,  # type: ignore[arg-type]
    )


@router.get("/free-agents/goalies", response_model=list[FreeAgentGoalieOut])
def list_goalies(
    min_ovr: int | None = Query(default=None),
    min_potential: int | None = Query(default=None),
    max_age: int | None = Query(default=None),
    sort: str = Query(default="ovr"),
    order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    return svc.list_free_agent_goalies(
        db,
        min_ovr=min_ovr,
        min_potential=min_potential,
        max_age=max_age,
        sort=sort,  # type: ignore[arg-type]
        order=order,  # type: ignore[arg-type]
    )


@router.post(
    "/teams/{team_id}/sign/skater/{skater_id}", response_model=SignReleaseSkaterOut
)
def sign_skater(team_id: int, skater_id: int, db: Session = Depends(get_db)):
    sk = svc.sign_skater(db, team_id, skater_id)
    db.commit()
    return sk


@router.post(
    "/teams/{team_id}/sign/goalie/{goalie_id}", response_model=SignReleaseGoalieOut
)
def sign_goalie(team_id: int, goalie_id: int, db: Session = Depends(get_db)):
    g = svc.sign_goalie(db, team_id, goalie_id)
    db.commit()
    return g


@router.post(
    "/teams/{team_id}/release/skater/{skater_id}", response_model=SignReleaseSkaterOut
)
def release_skater(team_id: int, skater_id: int, db: Session = Depends(get_db)):
    sk = svc.release_skater(db, team_id, skater_id)
    db.commit()
    return sk


@router.post(
    "/teams/{team_id}/release/goalie/{goalie_id}", response_model=SignReleaseGoalieOut
)
def release_goalie(team_id: int, goalie_id: int, db: Session = Depends(get_db)):
    g = svc.release_goalie(db, team_id, goalie_id)
    db.commit()
    return g
```

- [ ] **Step 4: Register the router**

Edit `backend/app/api/__init__.py`. Add `free_agents` to the imports and include its router:

```python
from app.api import (
    free_agents,
    games, gameplan, health, league, lineup, players, schedule, season, standings, stats, teams,
)

api_router = APIRouter(prefix="/api")
for r in (
    health.router,
    league.router,
    teams.router,
    lineup.router,
    schedule.router,
    standings.router,
    games.router,
    season.router,
    stats.router,
    players.router,
    gameplan.router,
    gameplan.list_router,
    free_agents.router,
):
    api_router.include_router(r)
```

- [ ] **Step 5: Run all FA-related tests**

Run: `cd backend && pytest tests/test_free_agents_api.py tests/test_sign_release_api.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && pytest -x`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/free_agents.py backend/app/api/__init__.py backend/tests/test_free_agents_api.py
git commit -m "feat(api): /free-agents listing + sign/release endpoints"
```

---

## Task 11: Backend doc updates

**Files:**
- Modify: `docs/product-scope.md`
- Modify: `docs/not-now.md`
- Create: `docs/phase-6.md`

- [ ] **Step 1: Update `docs/product-scope.md`**

Add a "Free Agents" section under "In Scope":

```markdown
### Free Agents

- Seeded pool of unsigned skaters and goalies generated at league creation.
- `/free-agents` page with filtering by position/min OVR/min potential/max age and sorting.
- The user team can sign free agents and release rostered players. Sign is instant; release shows a confirm modal.
- Released players return to the FA pool. Lineup slots referencing them are cleared automatically; stats are preserved.
- Implementation: `team_id` is nullable on `skater` and `goalie`. `team_id IS NULL` ⇔ free agent.
```

- [ ] **Step 2: Update `docs/not-now.md`**

Replace the "Free agency" line with:

```markdown
- Free agency (P1.1 implemented — basic FA pool + sign/release. Deeper systems still deferred: contracts, salary cap, AI signings, transfer windows.)
```

- [ ] **Step 3: Create `docs/phase-6.md`**

```markdown
# Phase 6 — Roster Agency

## P1.1 Free Agent Pool (implemented)

Seeded pool at league creation, FA listing endpoints, sign/release gated to the user team.

See `docs/superpowers/specs/2026-05-03-free-agent-pool-design.md` for the full design.

### Data model

- `skater.team_id` and `goalie.team_id` are nullable; `team_id IS NULL` ⇔ free agent. FK is `ON DELETE SET NULL`.
- All skater/goalie FKs on `lineup` are nullable so release can clear referenced slots.

### Endpoints

- `GET /api/free-agents/skaters` (filters: `position`, `min_ovr`, `min_potential`, `max_age`; sort: `ovr|potential|age|position`).
- `GET /api/free-agents/goalies` (same minus position).
- `POST /api/teams/{team_id}/sign/{skater|goalie}/{player_id}` — user team only.
- `POST /api/teams/{team_id}/release/{skater|goalie}/{player_id}` — user team only.

### Out of scope (P1.1)

AI signings, roster size limits, transfer windows, role/archetype attributes, contracts, salary cap, trades, draft, scouting.
```

- [ ] **Step 4: Commit**

```bash
git add docs/product-scope.md docs/not-now.md docs/phase-6.md
git commit -m "docs: free-agent pool (P1.1) scope and phase notes"
```

---

## Task 12: Frontend types and queries

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/queries/free-agents.ts`

- [ ] **Step 1: Inspect existing types/queries to match conventions**

Run: `head -80 frontend/src/api/types.ts && head -40 frontend/src/queries/teams.ts`
Note the shape of existing `*Out` types and `useX` query hooks; mirror them.

- [ ] **Step 2: Add FA types to `types.ts`**

Append to `frontend/src/api/types.ts`:

```typescript
export interface FreeAgentSkater {
  id: number;
  name: string;
  age: number;
  position: "LW" | "C" | "RW" | "LD" | "RD";
  potential: number;
  development_type: string;
  skating: number;
  shooting: number;
  passing: number;
  defense: number;
  physical: number;
  ovr: number;
}

export interface FreeAgentGoalie {
  id: number;
  name: string;
  age: number;
  potential: number;
  development_type: string;
  reflexes: number;
  positioning: number;
  rebound_control: number;
  puck_handling: number;
  mental: number;
  ovr: number;
}

export interface FreeAgentFilters {
  position?: FreeAgentSkater["position"];
  min_ovr?: number;
  min_potential?: number;
  max_age?: number;
  sort?: "ovr" | "potential" | "age" | "position";
  order?: "asc" | "desc";
}
```

- [ ] **Step 3: Create the query hooks**

Create `frontend/src/queries/free-agents.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  FreeAgentFilters,
  FreeAgentGoalie,
  FreeAgentSkater,
} from "../api/types";

const skaterQs = (f: FreeAgentFilters) => {
  const p = new URLSearchParams();
  if (f.position) p.set("position", f.position);
  if (f.min_ovr != null) p.set("min_ovr", String(f.min_ovr));
  if (f.min_potential != null) p.set("min_potential", String(f.min_potential));
  if (f.max_age != null) p.set("max_age", String(f.max_age));
  if (f.sort) p.set("sort", f.sort);
  if (f.order) p.set("order", f.order);
  return p.toString();
};

export const useFreeAgentSkaters = (filters: FreeAgentFilters) =>
  useQuery({
    queryKey: ["free-agents", "skaters", filters],
    queryFn: () => {
      const qs = skaterQs(filters);
      return api.get<FreeAgentSkater[]>(`/api/free-agents/skaters${qs ? `?${qs}` : ""}`);
    },
  });

export const useFreeAgentGoalies = (filters: Omit<FreeAgentFilters, "position">) =>
  useQuery({
    queryKey: ["free-agents", "goalies", filters],
    queryFn: () => {
      const qs = skaterQs(filters as FreeAgentFilters);
      return api.get<FreeAgentGoalie[]>(`/api/free-agents/goalies${qs ? `?${qs}` : ""}`);
    },
  });

const invalidate = (qc: ReturnType<typeof useQueryClient>, teamId: number) => {
  qc.invalidateQueries({ queryKey: ["free-agents"] });
  qc.invalidateQueries({ queryKey: ["teams", teamId] });
  qc.invalidateQueries({ queryKey: ["lineup", teamId] });
};

export const useSignSkater = (teamId: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (skaterId: number) =>
      api.post(`/api/teams/${teamId}/sign/skater/${skaterId}`),
    onSuccess: () => invalidate(qc, teamId),
  });
};

export const useSignGoalie = (teamId: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (goalieId: number) =>
      api.post(`/api/teams/${teamId}/sign/goalie/${goalieId}`),
    onSuccess: () => invalidate(qc, teamId),
  });
};

export const useReleaseSkater = (teamId: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (skaterId: number) =>
      api.post(`/api/teams/${teamId}/release/skater/${skaterId}`),
    onSuccess: () => invalidate(qc, teamId),
  });
};

export const useReleaseGoalie = (teamId: number) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (goalieId: number) =>
      api.post(`/api/teams/${teamId}/release/goalie/${goalieId}`),
    onSuccess: () => invalidate(qc, teamId),
  });
};
```

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/queries/free-agents.ts
git commit -m "feat(fe): free-agent types and query hooks"
```

---

## Task 13: `/free-agents` page

**Files:**
- Create: `frontend/src/routes/free-agents.tsx`

- [ ] **Step 1: Implement the page**

Create `frontend/src/routes/free-agents.tsx`:

```tsx
import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useLeague } from "../queries/league";
import {
  useFreeAgentSkaters,
  useFreeAgentGoalies,
  useSignSkater,
  useSignGoalie,
} from "../queries/free-agents";
import type { FreeAgentFilters } from "../api/types";
import { Shell } from "../components/Shell";
import { Button } from "../components/Button";
import { Table } from "../components/Table";

const POSITIONS = ["LW", "C", "RW", "LD", "RD"] as const;

const FreeAgentsPage = () => {
  const league = useLeague();
  const userTeamId = league.data?.user_team_id ?? null;
  const [tab, setTab] = useState<"skaters" | "goalies">("skaters");
  const [filters, setFilters] = useState<FreeAgentFilters>({
    sort: "ovr",
    order: "desc",
  });

  const skaters = useFreeAgentSkaters(tab === "skaters" ? filters : { sort: "ovr" });
  const goalies = useFreeAgentGoalies(tab === "goalies" ? filters : { sort: "ovr" });
  const signSkater = useSignSkater(userTeamId ?? 0);
  const signGoalie = useSignGoalie(userTeamId ?? 0);

  const update = <K extends keyof FreeAgentFilters>(k: K, v: FreeAgentFilters[K]) =>
    setFilters((f) => ({ ...f, [k]: v }));

  return (
    <Shell crumbs={["Free Agents"]}>
      <div style={{ padding: 16 }}>
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <Button onClick={() => setTab("skaters")} disabled={tab === "skaters"}>Skaters</Button>
          <Button onClick={() => setTab("goalies")} disabled={tab === "goalies"}>Goalies</Button>
        </div>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
          {tab === "skaters" && (
            <select
              value={filters.position ?? ""}
              onChange={(e) =>
                update("position", (e.target.value || undefined) as FreeAgentFilters["position"])
              }
            >
              <option value="">All positions</option>
              {POSITIONS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          )}
          <input
            type="number" placeholder="Min OVR"
            value={filters.min_ovr ?? ""}
            onChange={(e) => update("min_ovr", e.target.value ? Number(e.target.value) : undefined)}
          />
          <input
            type="number" placeholder="Min POT"
            value={filters.min_potential ?? ""}
            onChange={(e) => update("min_potential", e.target.value ? Number(e.target.value) : undefined)}
          />
          <input
            type="number" placeholder="Max age"
            value={filters.max_age ?? ""}
            onChange={(e) => update("max_age", e.target.value ? Number(e.target.value) : undefined)}
          />
          <select value={filters.sort ?? "ovr"} onChange={(e) => update("sort", e.target.value as FreeAgentFilters["sort"])}>
            <option value="ovr">OVR</option>
            <option value="potential">POT</option>
            <option value="age">Age</option>
            {tab === "skaters" && <option value="position">Position</option>}
          </select>
          <select value={filters.order ?? "desc"} onChange={(e) => update("order", e.target.value as "asc" | "desc")}>
            <option value="desc">Desc</option>
            <option value="asc">Asc</option>
          </select>
        </div>

        {userTeamId == null && (
          <div style={{ marginBottom: 12, color: "var(--ink-3)" }}>
            Set a user team to sign players.
          </div>
        )}

        {tab === "skaters" ? (
          <Table>
            <thead>
              <tr>
                <th>Name</th><th>Age</th><th>Pos</th><th>OVR</th><th>POT</th>
                <th>SKA</th><th>SHO</th><th>PAS</th><th>DEF</th><th>PHY</th><th></th>
              </tr>
            </thead>
            <tbody>
              {(skaters.data ?? []).map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td><td>{s.age}</td><td>{s.position}</td>
                  <td>{s.ovr}</td><td>{s.potential}</td>
                  <td>{s.skating}</td><td>{s.shooting}</td><td>{s.passing}</td>
                  <td>{s.defense}</td><td>{s.physical}</td>
                  <td>
                    <Button
                      onClick={() => signSkater.mutate(s.id)}
                      disabled={userTeamId == null || signSkater.isPending}
                    >
                      Sign
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>Name</th><th>Age</th><th>OVR</th><th>POT</th>
                <th>REF</th><th>POS</th><th>REB</th><th>PUC</th><th>MEN</th><th></th>
              </tr>
            </thead>
            <tbody>
              {(goalies.data ?? []).map((g) => (
                <tr key={g.id}>
                  <td>{g.name}</td><td>{g.age}</td>
                  <td>{g.ovr}</td><td>{g.potential}</td>
                  <td>{g.reflexes}</td><td>{g.positioning}</td><td>{g.rebound_control}</td>
                  <td>{g.puck_handling}</td><td>{g.mental}</td>
                  <td>
                    <Button
                      onClick={() => signGoalie.mutate(g.id)}
                      disabled={userTeamId == null || signGoalie.isPending}
                    >
                      Sign
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>
    </Shell>
  );
};

export const Route = createFileRoute("/free-agents")({ component: FreeAgentsPage });
```

> Inline styles match nothing in the codebase — replace them with the project's existing class conventions before committing if there's a clear pattern (e.g., `chl-*` classes used elsewhere).

- [ ] **Step 2: Regenerate route tree if needed**

Run: `cd frontend && npm run dev` (briefly) — TanStack Router will regenerate `routeTree.gen.ts`. Stop the dev server once the file updates. Or run the codegen step the project uses (check `package.json` scripts).

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Manual verify**

Run: `cd frontend && npm run dev` and `cd backend && uvicorn app.main:app --reload` in another terminal. Visit `http://localhost:5173/free-agents`.

Expected:
- Two tabs: Skaters / Goalies.
- Filter inputs work (changing position narrows the list, min OVR narrows the list).
- Sort changes work.
- Sign button moves a player into the user team — refresh the team page; player appears in roster.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/free-agents.tsx frontend/src/routeTree.gen.ts
git commit -m "feat(fe): /free-agents page with filter, sort, and sign"
```

---

## Task 14: Release button on team page + nav link

**Files:**
- Modify: `frontend/src/components/Shell.tsx`
- Modify: `frontend/src/routes/team.$teamId.tsx`

- [ ] **Step 1: Add the nav link**

Edit `frontend/src/components/Shell.tsx`. Append to the `NAV` array:

```typescript
{
  id: "free-agents",
  label: "Free Agents",
  to: "/free-agents",
  icon: "M3 7h18M3 12h18M3 17h18",
  match: (p) => p.startsWith("/free-agents"),
},
```

- [ ] **Step 2: Read the existing team page to find the roster table**

Run: `head -120 frontend/src/routes/team.\$teamId.tsx`
Locate the per-row markup for skaters and goalies.

- [ ] **Step 3: Add a Release button per row, gated to the user team**

In `frontend/src/routes/team.$teamId.tsx`:

```tsx
import { useReleaseSkater, useReleaseGoalie } from "../queries/free-agents";
import { useLeague } from "../queries/league";

// ...inside the component, near other hooks:
const league = useLeague();
const isUserTeam = league.data?.user_team_id === Number(teamId);
const releaseSkater = useReleaseSkater(Number(teamId));
const releaseGoalie = useReleaseGoalie(Number(teamId));

const onReleaseSkater = (id: number, name: string) => {
  if (window.confirm(`Release ${name}? They'll become a free agent.`)) {
    releaseSkater.mutate(id);
  }
};
const onReleaseGoalie = (id: number, name: string) => {
  if (window.confirm(`Release ${name}? They'll become a free agent.`)) {
    releaseGoalie.mutate(id);
  }
};
```

For each skater row, add a trailing cell:

```tsx
{isUserTeam && (
  <td>
    <Button onClick={() => onReleaseSkater(s.id, s.name)} disabled={releaseSkater.isPending}>
      Release
    </Button>
  </td>
)}
```

Same shape for goalies. If the table has a header row, add a matching empty `<th></th>` only when `isUserTeam` is true.

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Manual verify**

Run dev servers. Navigate to your user team's page, click Release on a skater, confirm. The player disappears from the roster. Navigate to `/free-agents` and confirm they appear there. Visit a non-user team — Release buttons must NOT appear.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Shell.tsx frontend/src/routes/team.\$teamId.tsx
git commit -m "feat(fe): release button on user-team roster + Free Agents nav link"
```

---

## Final verification

- [ ] Run the full backend suite: `cd backend && pytest -x`. Expect green.
- [ ] Run frontend type-check: `cd frontend && npx tsc --noEmit`. Expect green.
- [ ] Manual smoke: create a fresh league, open `/free-agents`, sign a player, release a player from your team's roster, confirm the released player shows up in `/free-agents`, simulate one matchday and confirm no errors.

If anything fails, fix in place — no new tasks needed unless a genuinely new issue surfaces.
