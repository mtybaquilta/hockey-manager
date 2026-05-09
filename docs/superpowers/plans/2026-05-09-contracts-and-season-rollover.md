# Contracts + Season Rollover (P1.3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add contracts as first-class entities, replace stored `age` with computed age from `birth_date`, introduce an `offseason` phase, and rework season rollover so it's contract-aware. Salary cap is intentionally deferred.

**Architecture:** New `contract` table with `status` (active/expired/terminated). All "is this player a FA / what are their terms" queries go through repository helpers. Player age computed from `birth_date` and a passed-in `season_year` at the service/API boundary (no global SQLAlchemy hybrid). `Season.year` integer drives aging implicitly. Rollover happens inside a `SELECT FOR UPDATE` on the current season to block double-clicks.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, pytest. Frontend: React + TanStack Query + Tailwind.

**Spec:** `docs/superpowers/specs/2026-05-09-contracts-and-season-rollover-design.md`

---

## File map

**New backend files:**
- `backend/app/models/contract.py` — `Contract` ORM model.
- `backend/app/schemas/contract.py` — Pydantic schemas (`ContractOut`, `SignContractIn`).
- `backend/app/services/contract_service.py` — repository helpers and lifecycle transitions.
- `backend/app/services/generation/contracts.py` — initial contract generation at league creation.
- `backend/alembic/versions/a7b8c9d0e1f2_phase8_contracts.py` — schema migration (rev id chosen to chain after `f6a7b8c9d0e1`).
- `backend/tests/test_contract_generation.py`
- `backend/tests/test_sign_contract_api.py`
- `backend/tests/test_release_preserves_contract.py`
- `backend/tests/test_trade_ntc.py`
- `backend/tests/test_age_helper.py`
- `backend/tests/test_offseason_phase.py`
- `frontend/src/queries/contracts.ts`
- `frontend/src/components/ContractBadge.tsx`
- `frontend/src/components/SignContractModal.tsx`

**Modified backend files:**
- `backend/app/models/skater.py` — add `birth_date`, drop `age`.
- `backend/app/models/goalie.py` — add `birth_date`, drop `age`.
- `backend/app/models/season.py` — add `year`.
- `backend/app/models/__init__.py` — export `Contract`.
- `backend/app/schemas/free_agents.py` — drop stored `age`, compute it.
- `backend/app/schemas/team.py` — same; expose contract.
- `backend/app/schemas/trade.py` — expose contract on trade-block items.
- `backend/app/services/free_agents_service.py` — accept terms in `sign_*`, terminate (not delete) in `release_*`, switch `age` filters to `birth_date`-based.
- `backend/app/services/trade_service.py` — exclude NTC, reject NTC trades, contract value modifier; replace `_age_modifier(age)` callers with computed age.
- `backend/app/services/advance_service.py` — playoffs end → `phase = "offseason"` instead of `status = "complete"`.
- `backend/app/services/season_rollover_service.py` — lock season, require `phase = "offseason"`, expire contracts, drop `age += 1`, set old season `status = "complete"`, set new `year`.
- `backend/app/services/generation/players.py` — emit `birth_date` instead of `age`.
- `backend/app/services/generation/free_agents.py` — same.
- `backend/app/services/league_service.py` — initialize `Season.year`, call contract generation.
- `backend/app/api/free_agents.py` — sign endpoints accept JSON body.
- `backend/app/errors.py` — add `OffseasonRequired`, `RolloverInProgress`, `ContractTermsInvalid`, `NoTradeClause`.
- `backend/tests/test_season_rollover.py` — update for offseason precondition + birth_date.
- `backend/tests/test_sign_release_api.py` — update for terms body and terminated-not-deleted.
- `backend/tests/test_trade_api.py` / `test_trade_block.py` — NTC paths.
- `backend/tests/test_models_smoke.py`, `test_league_creates_free_agents.py` — birth_date.

**Modified frontend files:**
- `frontend/src/queries/free-agents.ts` — sign mutation takes terms.
- `frontend/src/queries/season.ts` — start-new-season mutation; year + phase.
- `frontend/src/routes/free-agents.tsx` — Sign button opens modal.
- `frontend/src/routes/team.$teamId.tsx` — show contract column on roster.
- `frontend/src/routes/player.skater.$id.tsx`, `player.goalie.$id.tsx` — contract section.
- `frontend/src/routes/trade-block.tsx` — show contract terms; surface NTC reason.
- `frontend/src/routes/season-complete.tsx` — Start New Season button + expiring list.
- `frontend/src/routes/index.tsx` — offseason banner; year indicator.
- `frontend/src/components/Shell.tsx` — year indicator in header.

---

## Constants reference

These constants are referenced by multiple tasks. Define them once in `backend/app/services/generation/contracts.py`:

```python
LENGTH_WEIGHTS = [(1, 0.15), (2, 0.30), (3, 0.25), (4, 0.20), (5, 0.10)]
SALARY_FLOOR = 750
SALARY_OVR_BASELINE = 60
SALARY_OVR_FACTOR = 250
SALARY_MIN = 750
SALARY_MAX = 15000

def market_salary(ovr: int) -> int:
    raw = SALARY_FLOOR + SALARY_OVR_FACTOR * (ovr - SALARY_OVR_BASELINE)
    return max(SALARY_MIN, min(SALARY_MAX, raw))
```

Trade modifier constants (define in `trade_service.py`):

```python
CONTRACT_LENGTH_WEIGHT = 0.5
CONTRACT_SALARY_WEIGHT = 0.001
```

Sign-FA defaults (frontend, mirrors `market_salary`):

```ts
export const DEFAULT_SIGN_LENGTH = 2;
```

---

## Task 1: Alembic migration — Season.year, offseason phase value

**Files:**
- Create: `backend/app/alembic/versions/a7b8c9d0e1f2_phase8_contracts.py` *(actual path is `backend/alembic/versions/...`)*
- Test: covered by smoke test in Task 2

The migration is split across Tasks 1, 4 because it grows large; we'll write it in pieces and ship the whole revision in one file. Tasks 1, 4, 5 together produce the final migration. Commit after Task 5.

- [ ] **Step 1: Create the migration file with the year column upgrade**

Create `backend/alembic/versions/a7b8c9d0e1f2_phase8_contracts.py`:

```python
"""phase 8: contracts + birth_date + offseason

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-09 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Season.year (default 2025 for existing rows; non-nullable after backfill)
    op.add_column(
        "season",
        sa.Column("year", sa.Integer(), nullable=False, server_default="2025"),
    )
    # Drop the server_default so future inserts must specify year explicitly.
    op.alter_column("season", "year", server_default=None)


def downgrade() -> None:
    op.drop_column("season", "year")
```

The `phase` column already exists (set in `f6a7b8c9d0e1`); allowed values are managed in application code (free-form string). No DDL change for offseason.

- [ ] **Step 2: Run migration locally**

Run: `cd backend && alembic upgrade head`
Expected: migration runs cleanly; `season.year` exists; existing rows have `year = 2025`.

Verify in psql:
```
SELECT id, year FROM season;
```

---

## Task 2: Add `Season.year` to ORM + smoke test

**Files:**
- Modify: `backend/app/models/season.py`
- Test: `backend/tests/test_models_smoke.py`

- [ ] **Step 1: Add the field**

Edit `backend/app/models/season.py`, add after `phase`:

```python
    year: Mapped[int] = mapped_column(Integer, nullable=False)
```

- [ ] **Step 2: Add a smoke test**

Append to `backend/tests/test_models_smoke.py`:

```python
def test_season_has_year(db):
    from app.models import Season

    s = Season(seed=1, current_matchday=1, status="active", phase="regular_season", year=2026)
    db.add(s)
    db.flush()
    fetched = db.query(Season).filter_by(id=s.id).one()
    assert fetched.year == 2026
```

- [ ] **Step 3: Run the test**

Run: `cd backend && pytest tests/test_models_smoke.py::test_season_has_year -v`
Expected: PASS.

---

## Task 3: Update league creation to set `Season.year`

**Files:**
- Modify: `backend/app/services/league_service.py`

- [ ] **Step 1: Set the year on the new Season**

Edit `backend/app/services/league_service.py`. Replace:

```python
    season = Season(seed=seed_val, current_matchday=1, status="active")
```

with:

```python
    LEAGUE_START_YEAR = 2025
    season = Season(
        seed=seed_val,
        current_matchday=1,
        status="active",
        phase="regular_season",
        year=LEAGUE_START_YEAR,
    )
```

`LEAGUE_START_YEAR` is a local constant for now; subsequent specs may move it to a config module. The same year is used by player generation (Task 7) so birth_date math stays consistent.

- [ ] **Step 2: Verify existing league-creation tests still pass**

Run: `cd backend && pytest tests/test_league_creates_free_agents.py -v`
Expected: PASS (no behavioral change yet).

- [ ] **Step 3: Commit Tasks 1–3**

```bash
git add backend/alembic/versions/a7b8c9d0e1f2_phase8_contracts.py backend/app/models/season.py backend/app/services/league_service.py backend/tests/test_models_smoke.py
git commit -m "feat(season): add Season.year (default 2025)"
```

---

## Task 4: Migration — add `birth_date` to skater & goalie, backfill, drop `age`

**Files:**
- Modify: `backend/alembic/versions/a7b8c9d0e1f2_phase8_contracts.py`

- [ ] **Step 1: Append birth_date + drop age to upgrade()**

Edit the migration file. Append to `upgrade()` (after the year block):

```python
    # 2. Add birth_date to skater and goalie (nullable initially for backfill).
    op.add_column("skater", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("goalie", sa.Column("birth_date", sa.Date(), nullable=True))

    # Backfill: birth_date = (season.year - age, deterministic month/day from id).
    # Use the 'season' row with the smallest id as the league-start year anchor.
    bind = op.get_bind()
    league_start_year = bind.execute(
        sa.text("SELECT MIN(year) FROM season")
    ).scalar()
    if league_start_year is None:
        league_start_year = 2025

    # Deterministic month/day from id: mod 12 + 1 for month, mod 28 + 1 for day.
    bind.execute(
        sa.text(
            """
            UPDATE skater
            SET birth_date = make_date(:base_year - age, ((id % 12) + 1)::int, ((id % 28) + 1)::int)
            """
        ),
        {"base_year": league_start_year},
    )
    bind.execute(
        sa.text(
            """
            UPDATE goalie
            SET birth_date = make_date(:base_year - age, ((id % 12) + 1)::int, ((id % 28) + 1)::int)
            """
        ),
        {"base_year": league_start_year},
    )

    op.alter_column("skater", "birth_date", nullable=False)
    op.alter_column("goalie", "birth_date", nullable=False)

    # 3. Drop the age column.
    op.drop_column("skater", "age")
    op.drop_column("goalie", "age")
```

Append to `downgrade()`:

```python
    op.add_column("skater", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("goalie", sa.Column("age", sa.Integer(), nullable=True))
    bind = op.get_bind()
    league_start_year = bind.execute(sa.text("SELECT MIN(year) FROM season")).scalar() or 2025
    bind.execute(
        sa.text("UPDATE skater SET age = :y - EXTRACT(YEAR FROM birth_date)::int"),
        {"y": league_start_year},
    )
    bind.execute(
        sa.text("UPDATE goalie SET age = :y - EXTRACT(YEAR FROM birth_date)::int"),
        {"y": league_start_year},
    )
    op.alter_column("skater", "age", nullable=False)
    op.alter_column("goalie", "age", nullable=False)
    op.drop_column("skater", "birth_date")
    op.drop_column("goalie", "birth_date")
```

(Note: `downgrade` will also need to undo the contract table; we'll prepend that in Task 5.)

---

## Task 5: Migration — `contract` table + indexes

**Files:**
- Modify: `backend/alembic/versions/a7b8c9d0e1f2_phase8_contracts.py`

- [ ] **Step 1: Append the contract table to upgrade()**

```python
    # 4. Contract table.
    op.create_table(
        "contract",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("skater_id", sa.Integer(), sa.ForeignKey("skater.id", ondelete="CASCADE"), nullable=True),
        sa.Column("goalie_id", sa.Integer(), sa.ForeignKey("goalie.id", ondelete="CASCADE"), nullable=True),
        sa.Column("length", sa.Integer(), nullable=False),
        sa.Column("signed_season_year", sa.Integer(), nullable=False),
        sa.Column("expires_after_year", sa.Integer(), nullable=False),
        sa.Column("salary", sa.Integer(), nullable=False),
        sa.Column("no_trade_clause", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("terminated_season_year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(skater_id IS NOT NULL)::int + (goalie_id IS NOT NULL)::int = 1",
            name="contract_player_xor",
        ),
        sa.CheckConstraint(
            "status IN ('active','expired','terminated')",
            name="contract_status_check",
        ),
    )
    op.create_index(
        "ix_contract_skater_id_active",
        "contract",
        ["skater_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND skater_id IS NOT NULL"),
    )
    op.create_index(
        "ix_contract_goalie_id_active",
        "contract",
        ["goalie_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND goalie_id IS NOT NULL"),
    )
```

- [ ] **Step 2: Prepend contract drop to downgrade()**

At the *start* of `downgrade()`:

```python
    op.drop_index("ix_contract_goalie_id_active", table_name="contract")
    op.drop_index("ix_contract_skater_id_active", table_name="contract")
    op.drop_table("contract")
```

- [ ] **Step 3: Run migration**

Run: `cd backend && alembic upgrade head`
Expected: clean run; verify in psql:
```
\d contract
SELECT skater.id, birth_date FROM skater LIMIT 3;
```
Both should show populated rows.

- [ ] **Step 4: Run downgrade then upgrade to verify reversibility**

```
alembic downgrade -1
alembic upgrade head
```
Expected: both succeed.

- [ ] **Step 5: Commit migration**

```bash
git add backend/alembic/versions/a7b8c9d0e1f2_phase8_contracts.py
git commit -m "feat(db): contract table + birth_date columns; drop stored age"
```

---

## Task 6: ORM models — `Contract`, drop `age`, add `birth_date`

**Files:**
- Create: `backend/app/models/contract.py`
- Modify: `backend/app/models/skater.py`, `backend/app/models/goalie.py`, `backend/app/models/__init__.py`

- [ ] **Step 1: Create the Contract model**

```python
# backend/app/models/contract.py
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Contract(Base):
    __tablename__ = "contract"
    __table_args__ = (
        CheckConstraint(
            "(skater_id IS NOT NULL)::int + (goalie_id IS NOT NULL)::int = 1",
            name="contract_player_xor",
        ),
        CheckConstraint(
            "status IN ('active','expired','terminated')",
            name="contract_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    skater_id: Mapped[int | None] = mapped_column(
        ForeignKey("skater.id", ondelete="CASCADE"), nullable=True
    )
    goalie_id: Mapped[int | None] = mapped_column(
        ForeignKey("goalie.id", ondelete="CASCADE"), nullable=True
    )
    length: Mapped[int] = mapped_column(Integer, nullable=False)
    signed_season_year: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_after_year: Mapped[int] = mapped_column(Integer, nullable=False)
    salary: Mapped[int] = mapped_column(Integer, nullable=False)
    no_trade_clause: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    terminated_season_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 2: Replace `age` with `birth_date` on Skater and Goalie**

In `backend/app/models/skater.py`, replace the `age` line with:

```python
    birth_date: Mapped["date"] = mapped_column(Date, nullable=False)  # type: ignore[name-defined]
```

Add at top: `from datetime import date` and `from sqlalchemy import Date`. Use the actual `date` type (drop the `"date"` string form):

```python
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Skater(Base):
    __tablename__ = "skater"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("team.id", ondelete="SET NULL"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    position: Mapped[str] = mapped_column(String(2), nullable=False)
    skating: Mapped[int] = mapped_column(Integer, nullable=False)
    shooting: Mapped[int] = mapped_column(Integer, nullable=False)
    passing: Mapped[int] = mapped_column(Integer, nullable=False)
    defense: Mapped[int] = mapped_column(Integer, nullable=False)
    physical: Mapped[int] = mapped_column(Integer, nullable=False)
    potential: Mapped[int] = mapped_column(Integer, nullable=False)
    development_type: Mapped[str] = mapped_column(String(16), nullable=False)
```

Apply the analogous change in `backend/app/models/goalie.py`.

- [ ] **Step 3: Export Contract**

In `backend/app/models/__init__.py`, add `Contract` to imports and `__all__` (follow existing pattern).

- [ ] **Step 4: Smoke test**

Append to `backend/tests/test_models_smoke.py`:

```python
def test_contract_model_basic(db):
    from datetime import date
    from app.models import Contract, Skater, Team

    team = Team(name="Smoke", abbreviation="SMK")
    db.add(team)
    db.flush()
    sk = Skater(
        team_id=team.id, name="Smoke Player",
        birth_date=date(2000, 1, 1), position="C",
        skating=70, shooting=70, passing=70, defense=60, physical=70,
        potential=80, development_type="steady",
    )
    db.add(sk)
    db.flush()
    c = Contract(
        skater_id=sk.id, length=3, signed_season_year=2025,
        expires_after_year=2027, salary=2000, status="active",
    )
    db.add(c)
    db.flush()
    assert c.id is not None
    assert c.status == "active"
```

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_models_smoke.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/ backend/tests/test_models_smoke.py
git commit -m "feat(models): Contract; birth_date replaces age on Skater/Goalie"
```

---

## Task 7: Player age helper

**Files:**
- Create: `backend/app/services/player_age.py`
- Test: `backend/tests/test_age_helper.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_age_helper.py
from datetime import date

import pytest

from app.services.player_age import age_from_birth_date


def test_age_at_year_simple():
    assert age_from_birth_date(date(2000, 1, 1), 2025) == 25


def test_age_birthday_in_year_treated_uniformly():
    # No month adjustment in v1; everyone "ages" on the year boundary.
    assert age_from_birth_date(date(2000, 12, 31), 2025) == 25


def test_age_negative_year_raises():
    with pytest.raises(ValueError):
        age_from_birth_date(date(2025, 1, 1), 2024)
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd backend && pytest tests/test_age_helper.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# backend/app/services/player_age.py
from datetime import date


def age_from_birth_date(birth_date: date, season_year: int) -> int:
    """Compute a player's age as of the given season year.

    Year-boundary aging only (no month/day adjustment) — keeps the model
    simple while we don't have a real calendar.
    """
    age = season_year - birth_date.year
    if age < 0:
        raise ValueError(f"season_year {season_year} predates birth year {birth_date.year}")
    return age
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && pytest tests/test_age_helper.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/player_age.py backend/tests/test_age_helper.py
git commit -m "feat(player): age_from_birth_date helper"
```

---

## Task 8: Contract service — repository helpers and lifecycle transitions

**Files:**
- Create: `backend/app/services/contract_service.py`
- Test: `backend/tests/test_contract_service.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_contract_service.py
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Contract, Goalie, Skater, Team
from app.services import contract_service


def _make_skater(db, *, team_id=None):
    sk = Skater(
        team_id=team_id, name="Test", birth_date=date(2000, 1, 1), position="C",
        skating=70, shooting=70, passing=70, defense=60, physical=70,
        potential=80, development_type="steady",
    )
    db.add(sk)
    db.flush()
    return sk


def test_get_active_contract_skater_none(db):
    sk = _make_skater(db)
    assert contract_service.get_active_contract_for_skater(db, sk.id) is None


def test_create_active_contract_then_get(db):
    sk = _make_skater(db)
    c = contract_service.create_contract_for_skater(
        db, sk.id, length=2, signed_season_year=2025, salary=1500, no_trade_clause=False,
    )
    fetched = contract_service.get_active_contract_for_skater(db, sk.id)
    assert fetched is not None
    assert fetched.id == c.id
    assert c.expires_after_year == 2026


def test_partial_unique_index_blocks_two_actives(db):
    sk = _make_skater(db)
    contract_service.create_contract_for_skater(db, sk.id, length=2, signed_season_year=2025, salary=1500)
    with pytest.raises(IntegrityError):
        contract_service.create_contract_for_skater(db, sk.id, length=1, signed_season_year=2025, salary=1500)


def test_terminate_contract_flips_status_and_year(db):
    sk = _make_skater(db)
    c = contract_service.create_contract_for_skater(db, sk.id, length=3, signed_season_year=2025, salary=1500)
    contract_service.terminate_contract(db, c, season_year=2026)
    db.refresh(c)
    assert c.status == "terminated"
    assert c.terminated_season_year == 2026


def test_terminate_non_active_raises(db):
    sk = _make_skater(db)
    c = contract_service.create_contract_for_skater(db, sk.id, length=3, signed_season_year=2025, salary=1500)
    contract_service.terminate_contract(db, c, season_year=2026)
    with pytest.raises(contract_service.ContractStateError):
        contract_service.terminate_contract(db, c, season_year=2027)


def test_expire_contracts_for_year(db):
    sk_keep = _make_skater(db)
    sk_exp = _make_skater(db)
    contract_service.create_contract_for_skater(db, sk_keep.id, length=3, signed_season_year=2025, salary=1500)
    contract_service.create_contract_for_skater(db, sk_exp.id, length=1, signed_season_year=2025, salary=1500)
    expired = contract_service.expire_contracts_through_year(db, new_season_year=2026)
    assert expired == [(("skater", sk_exp.id))]
    assert contract_service.get_active_contract_for_skater(db, sk_keep.id) is not None
    assert contract_service.get_active_contract_for_skater(db, sk_exp.id) is None
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd backend && pytest tests/test_contract_service.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# backend/app/services/contract_service.py
from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Contract


class ContractStateError(DomainError):
    code = "ContractStateError"
    status = 409


def get_active_contract_for_skater(db: Session, skater_id: int) -> Contract | None:
    return (
        db.query(Contract)
        .filter(Contract.skater_id == skater_id, Contract.status == "active")
        .one_or_none()
    )


def get_active_contract_for_goalie(db: Session, goalie_id: int) -> Contract | None:
    return (
        db.query(Contract)
        .filter(Contract.goalie_id == goalie_id, Contract.status == "active")
        .one_or_none()
    )


def create_contract_for_skater(
    db: Session,
    skater_id: int,
    *,
    length: int,
    signed_season_year: int,
    salary: int,
    no_trade_clause: bool = False,
) -> Contract:
    c = Contract(
        skater_id=skater_id,
        length=length,
        signed_season_year=signed_season_year,
        expires_after_year=signed_season_year + length - 1,
        salary=salary,
        no_trade_clause=no_trade_clause,
        status="active",
    )
    db.add(c)
    db.flush()
    return c


def create_contract_for_goalie(
    db: Session,
    goalie_id: int,
    *,
    length: int,
    signed_season_year: int,
    salary: int,
    no_trade_clause: bool = False,
) -> Contract:
    c = Contract(
        goalie_id=goalie_id,
        length=length,
        signed_season_year=signed_season_year,
        expires_after_year=signed_season_year + length - 1,
        salary=salary,
        no_trade_clause=no_trade_clause,
        status="active",
    )
    db.add(c)
    db.flush()
    return c


def terminate_contract(db: Session, contract: Contract, *, season_year: int) -> None:
    if contract.status != "active":
        raise ContractStateError(
            f"contract {contract.id} status={contract.status!r}; cannot terminate"
        )
    contract.status = "terminated"
    contract.terminated_season_year = season_year
    db.flush()


def expire_contracts_through_year(
    db: Session, *, new_season_year: int
) -> list[tuple[str, int]]:
    """Flip every active contract whose expires_after_year < new_season_year
    to status='expired'. Returns a list of (player_type, player_id) for the
    affected players so callers can null team_id and clear lineup slots."""
    rows = (
        db.query(Contract)
        .filter(
            Contract.status == "active",
            Contract.expires_after_year < new_season_year,
        )
        .all()
    )
    out: list[tuple[str, int]] = []
    for c in rows:
        c.status = "expired"
        if c.skater_id is not None:
            out.append(("skater", c.skater_id))
        else:
            assert c.goalie_id is not None
            out.append(("goalie", c.goalie_id))
    db.flush()
    return out


def years_remaining(contract: Contract, *, season_year: int) -> int:
    return max(0, contract.expires_after_year - season_year + 1)
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd backend && pytest tests/test_contract_service.py -v`
Expected: all PASS. (`test_partial_unique_index_blocks_two_actives` may need `db.commit()` instead of `flush()` to surface the partial-index violation — if FAIL, change `db.flush()` to a `db.commit()` inside the test or move the second `create_contract_for_skater` after a `db.commit()`.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/contract_service.py backend/tests/test_contract_service.py
git commit -m "feat(contracts): contract_service with active lookup and lifecycle helpers"
```

---

## Task 9: Player generation — emit `birth_date` instead of `age`

**Files:**
- Modify: `backend/app/services/generation/players.py`, `backend/app/services/generation/free_agents.py`

- [ ] **Step 1: Update `generate_players_for_team`**

In `backend/app/services/generation/players.py`, change the function signature to accept `season_year` and replace age with birth_date:

```python
from datetime import date


def generate_players_for_team(
    rng: random.Random, db: Session, team_id: int, used_names: set[str], *, season_year: int
) -> None:
    for pos in SKATER_LAYOUT:
        skating = _attr(rng)
        shooting = _attr(rng)
        passing = _attr(rng)
        defense = _attr(rng) if pos in ("LD", "RD") else max(40, _attr(rng) - 5)
        physical = _attr(rng)
        age = rng.randint(19, 35)
        birth_year = season_year - age
        # Deterministic-but-varied month/day from rng for stable seed behavior.
        birth_date = date(birth_year, rng.randint(1, 12), rng.randint(1, 28))
        overall = skater_overall(skating, shooting, passing, defense, physical)
        db.add(
            Skater(
                team_id=team_id,
                name=make_player_name(rng, used_names),
                birth_date=birth_date,
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
    # Goalie generation: same pattern.
    for _ in range(GOALIE_COUNT):
        # ... existing attribute draws ...
        age = rng.randint(20, 36)
        birth_year = season_year - age
        birth_date = date(birth_year, rng.randint(1, 12), rng.randint(1, 28))
        # ... add Goalie(birth_date=birth_date, ...) instead of age=age
```

(Adapt the goalie block to existing structure — replicate the pattern.)

- [ ] **Step 2: Update `generate_teams` to pass `season_year`**

In `backend/app/services/generation/teams.py`, change `generate_teams` to accept `season_year` and forward it:

```python
def generate_teams(rng: random.Random, db: Session, *, season_year: int) -> list[Team]:
    used_names: set[str] = set()
    name_specs = sample_team_names(rng, TEAM_COUNT)
    teams: list[Team] = []
    for spec in name_specs:
        t = Team(name=spec["name"], abbreviation=spec["abbreviation"])
        db.add(t)
        db.flush()
        generate_players_for_team(rng, db, t.id, used_names, season_year=season_year)
        teams.append(t)
    db.flush()
    return teams
```

- [ ] **Step 3: Update FA pool generation**

In `backend/app/services/generation/free_agents.py`, accept `season_year` and use it to compute birth_date the same way. Replicate the pattern.

- [ ] **Step 4: Update `league_service.create_or_reset_league`**

```python
    season = Season(seed=seed_val, current_matchday=1, status="active", phase="regular_season", year=LEAGUE_START_YEAR)
    db.add(season)
    db.flush()
    rng = random.Random(seed_val)
    teams = generate_teams(rng, db, season_year=LEAGUE_START_YEAR)
    used_names = ...
    generate_free_agent_pool(rng, db, used_names, season_year=LEAGUE_START_YEAR)
```

- [ ] **Step 5: Run existing generation/league tests; expect failures, then update**

Run: `cd backend && pytest tests/test_league_creates_free_agents.py tests/test_free_agent_generation.py -v`

Update any test referencing `.age` on a Skater/Goalie to instead compute via `age_from_birth_date(p.birth_date, season.year)`. Existing tests likely assert "ages within 19..35" — change to similar assertion via the helper.

- [ ] **Step 6: Run again until green**

Run the same command. Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/generation/ backend/app/services/league_service.py backend/tests/
git commit -m "feat(generation): emit birth_date; threaded season_year through generation"
```

---

## Task 10: Initial contract generation

**Files:**
- Create: `backend/app/services/generation/contracts.py`
- Test: `backend/tests/test_contract_generation.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_contract_generation.py
import random
from collections import Counter

from app.models import Contract, Goalie, Skater
from app.services.generation.contracts import generate_initial_contracts


def test_every_rostered_player_has_active_contract(db_with_league):
    db = db_with_league
    skaters = db.query(Skater).filter(Skater.team_id.is_not(None)).all()
    goalies = db.query(Goalie).filter(Goalie.team_id.is_not(None)).all()
    contracts_by_skater = {c.skater_id for c in db.query(Contract).filter_by(status="active").all() if c.skater_id is not None}
    contracts_by_goalie = {c.goalie_id for c in db.query(Contract).filter_by(status="active").all() if c.goalie_id is not None}
    for s in skaters:
        assert s.id in contracts_by_skater, f"skater {s.id} has no active contract"
    for g in goalies:
        assert g.id in contracts_by_goalie


def test_free_agents_have_no_contract(db_with_league):
    db = db_with_league
    fa_skaters = db.query(Skater).filter(Skater.team_id.is_(None)).all()
    for s in fa_skaters:
        c = db.query(Contract).filter_by(skater_id=s.id, status="active").one_or_none()
        assert c is None


def test_lengths_distributed(db_with_league):
    db = db_with_league
    contracts = db.query(Contract).filter_by(status="active").all()
    counts = Counter(c.length for c in contracts)
    # Sanity: all weighted lengths are present and 2y is the modal weight.
    for length in [1, 2, 3, 4, 5]:
        assert counts[length] > 0
    assert counts[2] >= counts[1]  # 2y is heavier-weighted than 1y


def test_expiry_years_staggered(db_with_league):
    db = db_with_league
    contracts = db.query(Contract).filter_by(status="active").all()
    counts = Counter(c.expires_after_year for c in contracts)
    most_common_count = counts.most_common(1)[0][1]
    assert most_common_count <= len(contracts) * 0.5


def test_deterministic_from_seed(db_factory):
    # Two leagues with the same seed produce the same contracts.
    db1 = db_factory(seed=42)
    db2 = db_factory(seed=42)
    cs1 = sorted([(c.skater_id, c.goalie_id, c.length, c.salary, c.expires_after_year, c.signed_season_year) for c in db1.query(Contract).all()])
    cs2 = sorted([(c.skater_id, c.goalie_id, c.length, c.salary, c.expires_after_year, c.signed_season_year) for c in db2.query(Contract).all()])
    assert cs1 == cs2
```

Add fixtures to `backend/tests/conftest.py` if missing:

```python
@pytest.fixture()
def db_with_league(db):
    from app.services.league_service import create_or_reset_league
    create_or_reset_league(db, seed=12345)
    return db


@pytest.fixture()
def db_factory(engine):
    from sqlalchemy.orm import sessionmaker
    from app.services.league_service import create_or_reset_league

    def make(seed: int):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        S = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        s = S()
        create_or_reset_league(s, seed=seed)
        return s

    return make
```

(If your conftest already has equivalents, reuse them.)

- [ ] **Step 2: Run to confirm failure**

Run: `cd backend && pytest tests/test_contract_generation.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

```python
# backend/app/services/generation/contracts.py
import random

from sqlalchemy.orm import Session

from app.models import Goalie, Skater
from app.services import contract_service
from app.services.generation.players import goalie_overall, skater_overall

LENGTH_WEIGHTS = [(1, 0.15), (2, 0.30), (3, 0.25), (4, 0.20), (5, 0.10)]
SALARY_FLOOR = 750
SALARY_OVR_BASELINE = 60
SALARY_OVR_FACTOR = 250
SALARY_MIN = 750
SALARY_MAX = 15000


def market_salary(ovr: int) -> int:
    raw = SALARY_FLOOR + SALARY_OVR_FACTOR * (ovr - SALARY_OVR_BASELINE)
    return max(SALARY_MIN, min(SALARY_MAX, raw))


def _pick_length(rng: random.Random) -> int:
    r = rng.random()
    acc = 0.0
    for length, w in LENGTH_WEIGHTS:
        acc += w
        if r < acc:
            return length
    return LENGTH_WEIGHTS[-1][0]


def generate_initial_contracts(rng: random.Random, db: Session, *, season_year: int) -> None:
    """One active contract per rostered skater and goalie. FAs get nothing."""
    skaters = db.query(Skater).filter(Skater.team_id.is_not(None)).order_by(Skater.id).all()
    goalies = db.query(Goalie).filter(Goalie.team_id.is_not(None)).order_by(Goalie.id).all()

    for s in skaters:
        length = _pick_length(rng)
        signed = rng.randint(season_year - length + 1, season_year)
        ovr = skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)
        salary = market_salary(ovr)
        contract_service.create_contract_for_skater(
            db, s.id,
            length=length, signed_season_year=signed, salary=salary, no_trade_clause=False,
        )

    for g in goalies:
        length = _pick_length(rng)
        signed = rng.randint(season_year - length + 1, season_year)
        ovr = goalie_overall(g.reflexes, g.positioning, g.rebound_control, g.puck_handling, g.mental)
        salary = market_salary(ovr)
        contract_service.create_contract_for_goalie(
            db, g.id,
            length=length, signed_season_year=signed, salary=salary, no_trade_clause=False,
        )
    db.flush()
```

- [ ] **Step 4: Wire into league creation**

In `backend/app/services/league_service.py`, after the FA pool generation block, add:

```python
    from app.services.generation.contracts import generate_initial_contracts
    generate_initial_contracts(rng, db, season_year=LEAGUE_START_YEAR)
```

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_contract_generation.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/generation/contracts.py backend/app/services/league_service.py backend/tests/test_contract_generation.py backend/tests/conftest.py
git commit -m "feat(contracts): initial generation at league creation"
```

---

## Task 11: FA service — sign with terms, release preserves history

**Files:**
- Modify: `backend/app/services/free_agents_service.py`
- Modify: `backend/app/errors.py`
- Test: `backend/tests/test_release_preserves_contract.py`

- [ ] **Step 1: Add error type**

In `backend/app/errors.py`, add:

```python
class ContractTermsInvalid(DomainError):
    code = "ContractTermsInvalid"
    status = 422
```

- [ ] **Step 2: Write the failing release-preserves-contract test**

```python
# backend/tests/test_release_preserves_contract.py
from app.models import Contract, Skater
from app.services import contract_service, free_agents_service


def test_release_skater_terminates_contract(db_with_league):
    db = db_with_league
    sk = db.query(Skater).filter(Skater.team_id.is_not(None)).first()
    team_id = sk.team_id
    # The user team is set to teams[0] in create_or_reset_league; if sk isn't on it, skip.
    if team_id != db.query(Skater).first().team_id:
        # Adjust if needed; in practice the first skater is on the user team.
        pass
    active = contract_service.get_active_contract_for_skater(db, sk.id)
    assert active is not None

    free_agents_service.release_skater(db, team_id, sk.id)

    db.refresh(active)
    assert active.status == "terminated"
    assert active.terminated_season_year is not None
    assert sk.team_id is None
    # Active contract is gone but the row remains as history.
    assert contract_service.get_active_contract_for_skater(db, sk.id) is None
    assert db.query(Contract).filter_by(id=active.id).one_or_none() is not None
```

(Skip the user-team-mismatch detail by signing-then-releasing if your league fixture's user_team isn't the first team in iteration order — adapt as needed.)

- [ ] **Step 3: Run to confirm failure**

Run: `cd backend && pytest tests/test_release_preserves_contract.py -v`
Expected: FAIL.

- [ ] **Step 4: Update `release_skater` and `release_goalie`**

In `backend/app/services/free_agents_service.py`, replace the bodies of `release_skater` and `release_goalie` so they terminate the active contract. Find the current `Season.year` to pass:

```python
from app.services import contract_service


def _current_season_year(db: Session) -> int:
    season = db.query(Season).order_by(Season.id.desc()).first()
    if not season:
        raise NoActiveSeason("no active season")
    return season.year


def release_skater(db: Session, team_id: int, skater_id: int) -> Skater:
    _ensure_user_team(db, team_id)
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    if sk.team_id != team_id:
        raise PlayerNotOnTeam(f"skater {skater_id} is not on team {team_id}")
    _clear_skater_from_lineup(db, team_id, skater_id)
    active = contract_service.get_active_contract_for_skater(db, skater_id)
    if active is not None:
        contract_service.terminate_contract(db, active, season_year=_current_season_year(db))
    sk.team_id = None
    db.flush()
    return sk
```

Mirror the change in `release_goalie`. Add `from app.errors import NoActiveSeason` if not already present.

- [ ] **Step 5: Update `sign_skater` and `sign_goalie` to accept terms**

```python
def sign_skater(
    db: Session, team_id: int, skater_id: int, *,
    length: int, salary: int, no_trade_clause: bool = False,
) -> Skater:
    _ensure_user_team(db, team_id)
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    if sk.team_id is not None or contract_service.get_active_contract_for_skater(db, skater_id) is not None:
        raise PlayerNotFreeAgent(f"skater {skater_id} is not a free agent")
    _validate_terms(length, salary)
    sk.team_id = team_id
    contract_service.create_contract_for_skater(
        db, skater_id,
        length=length, signed_season_year=_current_season_year(db),
        salary=salary, no_trade_clause=no_trade_clause,
    )
    db.flush()
    return sk
```

Add `_validate_terms`:

```python
from app.errors import ContractTermsInvalid
from app.services.generation.contracts import SALARY_MAX, SALARY_MIN


def _validate_terms(length: int, salary: int) -> None:
    if not (1 <= length <= 8):
        raise ContractTermsInvalid(f"length {length} not in [1, 8]")
    if not (SALARY_MIN <= salary <= SALARY_MAX):
        raise ContractTermsInvalid(f"salary {salary} not in [{SALARY_MIN}, {SALARY_MAX}]")
```

Mirror in `sign_goalie`.

- [ ] **Step 6: Update FA filters that referenced `Skater.age`**

Replace `Skater.age <= max_age` filter with a birth_date-based filter. Add a helper in the same file:

```python
from datetime import date


def _max_birth_date_for_max_age(season_year: int, max_age: int) -> date:
    # Player must be at most max_age in `season_year`. age = season_year - birth_year.
    # max_age implies birth_year >= season_year - max_age, i.e. birth_date >= Jan 1 of that year.
    return date(season_year - max_age, 1, 1)
```

In `list_free_agent_skaters`/`list_free_agent_goalies`, replace `q.filter(Skater.age <= max_age)` with:

```python
    if max_age is not None:
        season_year = _current_season_year(db)
        q = q.filter(Skater.birth_date >= _max_birth_date_for_max_age(season_year, max_age))
```

For the `age` sort key, replace `Skater.age` with `Skater.birth_date` and **invert** order (older birth_date = younger player, so default desc/asc semantics flip). Simpler approach: leave the sort key as `Skater.birth_date` and document that "age desc" sorts oldest first by birth_date asc:

```python
    sort_map = {
        "ovr": _skater_ovr_expr(),
        "potential": Skater.potential,
        # "age" sort uses birth_date with inverted direction.
        "age": Skater.birth_date,
        "position": Skater.position,
    }
    col = sort_map[sort]
    if sort == "age":
        q = q.order_by(col.desc() if order == "asc" else col.asc())
    else:
        q = q.order_by(col.asc() if order == "asc" else col.desc())
```

Mirror in goalies.

- [ ] **Step 7: Run all FA-related tests**

Run: `cd backend && pytest tests/test_free_agents_api.py tests/test_release_preserves_contract.py tests/test_sign_release_api.py -v`

Update existing tests in `test_sign_release_api.py` to pass terms in the body (use the service signatures here; API task comes next):

If your tests call `sign_skater(db, team, id)` directly, update to `sign_skater(db, team, id, length=2, salary=1500)`.

Expected: PASS after edits.

- [ ] **Step 8: Commit**

```bash
git add backend/app/errors.py backend/app/services/free_agents_service.py backend/tests/
git commit -m "feat(fa): sign with terms; release terminates contract (history preserved)"
```

---

## Task 12: Sign FA endpoint accepts JSON body

**Files:**
- Modify: `backend/app/api/free_agents.py`
- Create: `backend/app/schemas/contract.py`
- Test: `backend/tests/test_sign_contract_api.py`

- [ ] **Step 1: Create Pydantic schemas**

```python
# backend/app/schemas/contract.py
from pydantic import BaseModel, ConfigDict, Field


class SignContractIn(BaseModel):
    length: int = Field(..., ge=1, le=8)
    salary: int = Field(..., ge=750, le=15000)
    no_trade_clause: bool = False


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    length: int
    signed_season_year: int
    expires_after_year: int
    salary: int
    no_trade_clause: bool
    status: str
```

- [ ] **Step 2: Write failing API test**

```python
# backend/tests/test_sign_contract_api.py
def test_sign_skater_with_terms(client, db_with_league):
    # find a FA skater
    fa = client.get("/api/free-agents/skaters").json()[0]
    user_team_id = client.get("/api/season").json().get("user_team_id") or db_with_league.query(...).first().user_team_id
    body = {"length": 3, "salary": 2000, "no_trade_clause": True}
    res = client.post(f"/api/teams/{user_team_id}/sign/skater/{fa['id']}", json=body)
    assert res.status_code == 200
    assert res.json()["team_id"] == user_team_id
    assert res.json()["contract"]["length"] == 3
    assert res.json()["contract"]["no_trade_clause"] is True


def test_sign_skater_invalid_length(client, db_with_league):
    fa = client.get("/api/free-agents/skaters").json()[0]
    user_team_id = ... # as above
    body = {"length": 0, "salary": 2000}
    res = client.post(f"/api/teams/{user_team_id}/sign/skater/{fa['id']}", json=body)
    assert res.status_code == 422
```

(Use the existing `client` fixture pattern from your suite — see other test_*_api files.)

- [ ] **Step 3: Run to confirm failure**

Expected: FAIL — endpoint doesn't accept body yet.

- [ ] **Step 4: Update endpoint**

In `backend/app/api/free_agents.py`:

```python
from app.schemas.contract import ContractOut, SignContractIn


class SignSkaterOut(SignReleaseSkaterOut):
    contract: ContractOut


class SignGoalieOut(SignReleaseGoalieOut):
    contract: ContractOut


@router.post("/teams/{team_id}/sign/skater/{skater_id}", response_model=SignSkaterOut)
def sign_skater(team_id: int, skater_id: int, body: SignContractIn, db: Session = Depends(get_db)):
    sk = svc.sign_skater(
        db, team_id, skater_id,
        length=body.length, salary=body.salary, no_trade_clause=body.no_trade_clause,
    )
    contract = contract_service.get_active_contract_for_skater(db, skater_id)
    db.commit()
    return SignSkaterOut.model_validate({**sk.__dict__, "contract": contract})
```

(Apply same pattern for goalies.)

Note: `FreeAgentSkaterOut` currently exposes `age` directly from the model. Now that age is a computed value, change `FreeAgentSkaterOut` to a `computed_field` that takes `birth_date`:

```python
# in backend/app/schemas/free_agents.py
from datetime import date

from app.services.player_age import age_from_birth_date


class FreeAgentSkaterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    birth_date: date
    position: str
    # ... existing fields except age ...

    # Age is contextual; expose as a function of season_year supplied by serializer.
    # Simplest: add a top-level helper that wraps the model with a season_year.
```

Because Pydantic can't pass an arbitrary `season_year` through `from_attributes=True`, **change the schema to accept and pass `current_season_year` via the route handler**. Implementation: the route handler reads `Season.year`, calls a small adapter `to_skater_out(skater, season_year)` that returns a dict, and feeds that dict into Pydantic. Define this helper in the schemas module:

```python
def skater_to_out(s, season_year: int) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "age": age_from_birth_date(s.birth_date, season_year),
        "position": s.position,
        "potential": s.potential,
        "development_type": s.development_type,
        "skating": s.skating, "shooting": s.shooting, "passing": s.passing,
        "defense": s.defense, "physical": s.physical,
    }
```

And keep `FreeAgentSkaterOut` with `age: int` as a regular field. Update each endpoint that returned `Skater` rows to map through `skater_to_out(s, season_year)`.

(Mirror for goalie.)

- [ ] **Step 5: Run sign-API tests until green**

Run: `cd backend && pytest tests/test_sign_contract_api.py tests/test_sign_release_api.py tests/test_free_agents_api.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/free_agents.py backend/app/schemas/ backend/tests/
git commit -m "feat(api): /sign accepts contract terms; serialize computed age"
```

---

## Task 13: Trade integration — NTC blocks, contract value modifier

**Files:**
- Modify: `backend/app/services/trade_service.py`
- Modify: `backend/app/errors.py`
- Test: `backend/tests/test_trade_ntc.py`

- [ ] **Step 1: Add error**

In `backend/app/errors.py`:

```python
class NoTradeClause(DomainError):
    code = "NoTradeClause"
    status = 409
```

- [ ] **Step 2: Write failing tests**

```python
# backend/tests/test_trade_ntc.py
from app.models import Contract, Skater
from app.services import contract_service, trade_service


def test_trade_block_excludes_ntc_holders(db_with_league):
    # Pick any skater; flip their contract NTC; recompute trade-block and verify exclusion.
    db = db_with_league
    sk = db.query(Skater).filter(Skater.team_id.is_not(None)).first()
    c = contract_service.get_active_contract_for_skater(db, sk.id)
    c.no_trade_clause = True
    db.flush()
    block = trade_service.compute_trade_block(db)
    for entry in block:
        assert entry["player_id"] != sk.id or entry["player_type"] != "skater"


def test_propose_trade_rejected_for_ntc(db_with_league, client):
    # Set NTC on the targeted player; expect 409 NoTradeClause.
    ...
```

(Adapt to the existing `compute_trade_block` and propose-trade entry points.)

- [ ] **Step 3: Run to confirm failure**

Expected: FAIL.

- [ ] **Step 4: Implement NTC exclusion in trade-block**

In `backend/app/services/trade_service.py`, find the function that computes block candidates. Filter out NTC holders by joining/looking up active contracts:

```python
def _has_ntc(db, player_type: str, player_id: int) -> bool:
    if player_type == "skater":
        c = contract_service.get_active_contract_for_skater(db, player_id)
    else:
        c = contract_service.get_active_contract_for_goalie(db, player_id)
    return bool(c and c.no_trade_clause)
```

When building the block, skip candidates where `_has_ntc(...)` is true.

- [ ] **Step 5: Implement NTC rejection in propose_trade**

Find the propose-trade entry point. Before evaluating value:

```python
from app.errors import NoTradeClause
from app.services import contract_service

if _has_ntc(db, offered_type, offered_id) or _has_ntc(db, target_type, target_id):
    raise NoTradeClause("trade rejected: no-trade clause")
```

- [ ] **Step 6: Implement contract value modifier**

Locate the value computation (currently `value = ovr + age_modifier + position_need_modifier`). Add:

```python
CONTRACT_LENGTH_WEIGHT = 0.5
CONTRACT_SALARY_WEIGHT = 0.001


def _contract_modifier(db, player_type: str, player_id: int, season_year: int, ovr: int) -> float:
    if player_type == "skater":
        c = contract_service.get_active_contract_for_skater(db, player_id)
    else:
        c = contract_service.get_active_contract_for_goalie(db, player_id)
    if not c:
        return 0.0
    yrs = max(0, c.expires_after_year - season_year + 1)
    market = market_salary(ovr)
    return (yrs - 2) * CONTRACT_LENGTH_WEIGHT - (c.salary - market) * CONTRACT_SALARY_WEIGHT
```

Add `from app.services.generation.contracts import market_salary`.

In the value computation, sum into the existing total:

```python
value = ovr + age_modifier + position_need_modifier + int(round(_contract_modifier(db, ...)))
```

- [ ] **Step 7: Replace `_age_modifier(s.age)` with computed-age**

Wherever the trade evaluator reads `s.age` (e.g. `_age_modifier(s.age)`, the `s.age >= 32` veteran-reason check), replace with `age_from_birth_date(s.birth_date, season.year)`.

- [ ] **Step 8: Run tests until green**

Run: `cd backend && pytest tests/test_trade_ntc.py tests/test_trade_block.py tests/test_trade_api.py -v`
Update any test asserting on previous value math to account for the new modifier (existing equal-value assertions should still hold since both sides have the same modifier baseline of 0 for default contracts).

- [ ] **Step 9: Commit**

```bash
git add backend/app/errors.py backend/app/services/trade_service.py backend/tests/
git commit -m "feat(trades): NTC blocks; light contract value modifier"
```

---

## Task 14: Offseason phase — `_advance_playoffs` flips to offseason

**Files:**
- Modify: `backend/app/services/advance_service.py`
- Test: `backend/tests/test_offseason_phase.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_offseason_phase.py
from app.models import Season
from app.services.advance_service import advance_matchday


def test_playoffs_end_transitions_to_offseason(db_with_league):
    db = db_with_league
    # Sim until the season is finished. Use sim-to-end helper.
    while True:
        res = advance_matchday(db)
        if res["season_phase"] == "offseason":
            break
        if res["season_phase"] == "regular_season" and res["season_status"] != "active":
            break
    season = db.query(Season).order_by(Season.id.desc()).first()
    assert season.phase == "offseason"
    assert season.status == "active"
    assert season.champion_team_id is not None
```

- [ ] **Step 2: Run to confirm failure**

Expected: FAIL — currently sets `status = "complete"`.

- [ ] **Step 3: Update `_advance_playoffs`**

In `backend/app/services/advance_service.py`, find:

```python
            season.champion_team_id = final.winner_team_id if final else None
            season.status = "complete"
```

Replace with:

```python
            season.champion_team_id = final.winner_team_id if final else None
            season.phase = "offseason"
            # status stays "active" — see spec's status/phase semantics.
```

- [ ] **Step 4: Update any place that returns `season_status` to also return phase**

Confirm `advance_matchday` returns `season_phase` in its dict (it does — line ~308). Good.

- [ ] **Step 5: Run test until green**

Run: `cd backend && pytest tests/test_offseason_phase.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/advance_service.py backend/tests/test_offseason_phase.py
git commit -m "feat(season): playoffs end → phase=offseason (status stays active)"
```

---

## Task 15: Rollover — require offseason, expire contracts, age via year

**Files:**
- Modify: `backend/app/services/season_rollover_service.py`
- Modify: `backend/app/errors.py`
- Modify: `backend/tests/test_season_rollover.py`

- [ ] **Step 1: Add error**

In `backend/app/errors.py`:

```python
class OffseasonRequired(DomainError):
    code = "OffseasonRequired"
    status = 409
```

- [ ] **Step 2: Update `start_next_season`**

Major changes. Replace the precondition block and ageing logic:

```python
from sqlalchemy import select

from app.errors import OffseasonRequired
from app.services import contract_service
from app.services.free_agents_service import _clear_skater_from_lineup, _clear_goalie_from_lineup
from app.services.player_age import age_from_birth_date


def start_next_season(db: Session) -> dict:
    # Lock the latest season row to block double-rollover.
    season = (
        db.execute(
            select(Season).order_by(Season.id.desc()).limit(1).with_for_update()
        )
        .scalars()
        .first()
    )
    if season is None:
        raise NoActiveSeason("no active season")
    if season.phase != "offseason":
        raise OffseasonRequired(
            f"season {season.id} phase={season.phase!r}; expected 'offseason'"
        )

    # Compute league perf signals against the season we are leaving.
    league_ppg = _league_skater_ppg(db, season.id)
    league_sv = _league_save_pct(db, season.id)

    new_seed = (season.seed * 31 + season.id) & 0x7FFFFFFF
    new_year = season.year + 1
    new_season = Season(
        seed=new_seed,
        user_team_id=season.user_team_id,
        current_matchday=1,
        status="active",
        phase="regular_season",
        year=new_year,
    )
    db.add(new_season)
    db.flush()

    # Player development still runs per-player. Age is now computed from birth_date.
    skaters = db.query(Skater).all()
    goalies = db.query(Goalie).all()

    for s in skaters:
        age_before = age_from_birth_date(s.birth_date, season.year)
        age_after = age_from_birth_date(s.birth_date, new_year)
        perf = _skater_perf_signal(db, season.id, s.id, league_ppg)
        inp = PlayerDevInput(
            player_id=s.id, player_type="skater", age=age_before,
            attrs={"skating": s.skating, "shooting": s.shooting, "passing": s.passing, "defense": s.defense, "physical": s.physical},
            potential=s.potential, development_type=s.development_type, perf_signal=perf,
        )
        result = develop_player(inp, season_seed=new_seed)
        _persist_progression(
            db, from_season_id=season.id, to_season_id=new_season.id,
            player_type="skater", player_id=s.id,
            age_before=age_before, age_after=age_after,
            potential=s.potential, development_type=s.development_type, result=result,
        )
        _apply_skater_development(s, result)
        # Note: no s.age += 1 — age is implicit via new_season.year.

    for g in goalies:
        age_before = age_from_birth_date(g.birth_date, season.year)
        age_after = age_from_birth_date(g.birth_date, new_year)
        perf = _goalie_perf_signal(db, season.id, g.id, league_sv)
        inp = PlayerDevInput(
            player_id=g.id, player_type="goalie", age=age_before,
            attrs={"reflexes": g.reflexes, "positioning": g.positioning, "rebound_control": g.rebound_control, "puck_handling": g.puck_handling, "mental": g.mental},
            potential=g.potential, development_type=g.development_type, perf_signal=perf,
        )
        result = develop_player(inp, season_seed=new_seed)
        _persist_progression(
            db, from_season_id=season.id, to_season_id=new_season.id,
            player_type="goalie", player_id=g.id,
            age_before=age_before, age_after=age_after,
            potential=g.potential, development_type=g.development_type, result=result,
        )
        _apply_goalie_development(g, result)

    # Expire contracts whose expires_after_year < new_year and free those players.
    expired_players = contract_service.expire_contracts_through_year(db, new_season_year=new_year)
    for player_type, player_id in expired_players:
        if player_type == "skater":
            sk = db.query(Skater).filter_by(id=player_id).one()
            if sk.team_id is not None:
                _clear_skater_from_lineup(db, sk.team_id, sk.id)
                sk.team_id = None
        else:
            g = db.query(Goalie).filter_by(id=player_id).one()
            if g.team_id is not None:
                _clear_goalie_from_lineup(db, g.team_id, g.id)
                g.team_id = None

    # Schedule + standings for new season.
    team_ids = [t.id for t in db.query(Team).order_by(Team.id).all()]
    rng = random.Random(new_seed)
    generate_schedule(rng, db, new_season.id, team_ids)
    for tid in team_ids:
        db.add(Standing(team_id=tid, season_id=new_season.id))

    # Close the prior season.
    season.status = "complete"
    db.flush()

    return {
        "from_season_id": season.id,
        "to_season_id": new_season.id,
        "new_year": new_year,
        "expired_player_count": len(expired_players),
    }
```

- [ ] **Step 3: Update existing rollover tests**

Open `backend/tests/test_season_rollover.py`. For tests that set `season.status = "complete"` to satisfy the precondition, change to `season.phase = "offseason"`.

For tests that assert on `s.age += 1` semantics, update assertions:

```python
# Before:
assert skater.age == prev_age + 1
# After:
from app.services.player_age import age_from_birth_date
new_year = db.query(Season).filter_by(status="active").one().year
assert age_from_birth_date(skater.birth_date, new_year) == prev_age + 1
```

Add a new test:

```python
def test_rollover_expires_contracts_and_frees_players(db_with_league):
    from app.services import contract_service
    from app.services import season_rollover_service
    from app.models import Season, Skater

    db = db_with_league
    # Force a contract to expire this rollover.
    sk = db.query(Skater).filter(Skater.team_id.is_not(None)).first()
    c = contract_service.get_active_contract_for_skater(db, sk.id)
    season = db.query(Season).order_by(Season.id.desc()).one()
    c.expires_after_year = season.year  # expires after this year
    season.phase = "offseason"
    db.flush()

    season_rollover_service.start_next_season(db)

    db.refresh(c)
    db.refresh(sk)
    assert c.status == "expired"
    assert sk.team_id is None


def test_rollover_blocked_outside_offseason(db_with_league):
    from app.errors import OffseasonRequired
    from app.services import season_rollover_service

    db = db_with_league
    with pytest.raises(OffseasonRequired):
        season_rollover_service.start_next_season(db)
```

- [ ] **Step 4: Run tests until green**

Run: `cd backend && pytest tests/test_season_rollover.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/errors.py backend/app/services/season_rollover_service.py backend/tests/test_season_rollover.py
git commit -m "feat(rollover): require offseason; expire contracts; age via Season.year"
```

---

## Task 16: Frontend — sign modal + free-agents route

**Files:**
- Create: `frontend/src/components/SignContractModal.tsx`
- Modify: `frontend/src/queries/free-agents.ts`
- Modify: `frontend/src/routes/free-agents.tsx`

- [ ] **Step 1: Update mutation signature**

In `frontend/src/queries/free-agents.ts`, change the sign mutation to take a body:

```ts
type SignTerms = { length: number; salary: number; no_trade_clause: boolean };

export function useSignSkater(teamId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ skaterId, terms }: { skaterId: number; terms: SignTerms }) => {
      const res = await fetch(`/api/teams/${teamId}/sign/skater/${skaterId}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(terms),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["free-agents"] });
      qc.invalidateQueries({ queryKey: ["team", teamId] });
    },
  });
}
```

(Mirror for goalies.)

- [ ] **Step 2: Build the modal component**

```tsx
// frontend/src/components/SignContractModal.tsx
import { useState } from "react";

type Props = {
  player: { id: number; name: string; ovr: number };
  defaultSalary: number;
  onClose: () => void;
  onSubmit: (terms: { length: number; salary: number; no_trade_clause: boolean }) => void;
  submitting?: boolean;
};

export function SignContractModal({ player, defaultSalary, onClose, onSubmit, submitting }: Props) {
  const [length, setLength] = useState(2);
  const [salary, setSalary] = useState(defaultSalary);
  const [ntc, setNtc] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-lg p-6 w-96 max-w-full" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold mb-4">Sign {player.name}</h2>
        <label className="block mb-3">
          <span className="text-sm font-medium">Length (years)</span>
          <select className="mt-1 block w-full border rounded px-2 py-1" value={length} onChange={(e) => setLength(Number(e.target.value))}>
            {[1,2,3,4,5,6,7,8].map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </label>
        <label className="block mb-3">
          <span className="text-sm font-medium">Salary (${(salary/1000).toFixed(2)}M / yr)</span>
          <input type="number" min={750} max={15000} step={50} className="mt-1 block w-full border rounded px-2 py-1"
                 value={salary} onChange={(e) => setSalary(Number(e.target.value))} />
        </label>
        <label className="flex items-center gap-2 mb-4">
          <input type="checkbox" checked={ntc} onChange={(e) => setNtc(e.target.checked)} />
          <span className="text-sm">No-Trade Clause</span>
        </label>
        <div className="flex justify-end gap-2">
          <button className="px-3 py-1 border rounded" onClick={onClose} disabled={submitting}>Cancel</button>
          <button className="px-3 py-1 bg-blue-600 text-white rounded"
                  onClick={() => onSubmit({ length, salary, no_trade_clause: ntc })}
                  disabled={submitting}>Sign</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wire into `free-agents` route**

In `frontend/src/routes/free-agents.tsx`, replace the existing one-click Sign button with a button that opens the modal. Default salary mirrors backend formula:

```ts
const SALARY_FLOOR = 750;
const SALARY_OVR_BASELINE = 60;
const SALARY_OVR_FACTOR = 250;
const SALARY_MIN = 750;
const SALARY_MAX = 15000;

function suggestedSalary(ovr: number) {
  const raw = SALARY_FLOOR + SALARY_OVR_FACTOR * (ovr - SALARY_OVR_BASELINE);
  return Math.max(SALARY_MIN, Math.min(SALARY_MAX, raw));
}
```

State + render: track `signing` as the FA player object; when set, render the modal; on submit, call the mutation; on success/cancel, clear `signing`.

- [ ] **Step 4: Verify by running the dev server**

```
cd frontend && npm run dev
```

Open `/free-agents`, click Sign on a player, fill the modal, confirm — the player should disappear from the FA list and appear on the user team.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SignContractModal.tsx frontend/src/queries/free-agents.ts frontend/src/routes/free-agents.tsx
git commit -m "feat(fe): sign FA modal with length/salary/NTC"
```

---

## Task 17: Frontend — contract badge + roster + player detail

**Files:**
- Create: `frontend/src/components/ContractBadge.tsx`
- Modify: `frontend/src/routes/team.$teamId.tsx`, `player.skater.$id.tsx`, `player.goalie.$id.tsx`
- Modify: backend response shapes to include contract on relevant endpoints

- [ ] **Step 1: Add contract to roster + player-detail backend payloads**

In `backend/app/schemas/team.py` (and the player-detail schemas referenced by the player routes), add an optional `contract: ContractOut | None` field. In the corresponding service/route, fetch via `contract_service.get_active_contract_for_*` and attach.

- [ ] **Step 2: Build `ContractBadge`**

```tsx
// frontend/src/components/ContractBadge.tsx
type Props = {
  contract: { length: number; expires_after_year: number; salary: number; no_trade_clause: boolean } | null;
  currentYear: number;
};

export function ContractBadge({ contract, currentYear }: Props) {
  if (!contract) return <span className="text-xs text-gray-400">UFA</span>;
  const yrs = Math.max(0, contract.expires_after_year - currentYear + 1);
  const m = (contract.salary / 1000).toFixed(2);
  return (
    <span className="text-xs">
      {yrs}y · ${m}M
      {contract.no_trade_clause && <span className="ml-1 px-1 rounded bg-amber-100 text-amber-800">NTC</span>}
    </span>
  );
}
```

- [ ] **Step 3: Render badge on roster table and player detail pages**

Add a "Contract" column to the team roster table; render `<ContractBadge contract={p.contract} currentYear={season.year} />`. On `player.skater.$id.tsx` and `player.goalie.$id.tsx`, add a "Contract" section showing length, signed year, expires year, salary, NTC.

`currentYear` comes from the season query (Task 18 ensures `Season.year` is exposed by the season endpoint).

- [ ] **Step 4: Manual verify in browser**

Confirm badges render correctly for rostered players and FAs.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/ backend/app/api/ frontend/src/components/ContractBadge.tsx frontend/src/routes/team.$teamId.tsx frontend/src/routes/player.*.tsx
git commit -m "feat(fe): contract badge on roster + player detail; expose contract on payloads"
```

---

## Task 18: Frontend + backend — season year, offseason banner, Start New Season

**Files:**
- Modify: `backend/app/api/season.py` (rollover endpoint precondition + response; expose year/phase on status endpoint)
- Modify: `frontend/src/queries/season.ts`
- Modify: `frontend/src/routes/season-complete.tsx`, `frontend/src/routes/index.tsx`
- Modify: `frontend/src/components/Shell.tsx`

- [ ] **Step 1: Update `/season` GET to expose year + phase**

Find the season status endpoint (existing). Add `year: int` and `phase: str` to its response model. The existing `phase` is already in the data; surface it.

- [ ] **Step 2: Update rollover endpoint**

The existing endpoint that wraps `season_rollover_service.start_next_season` should now require `phase = "offseason"`; the service already enforces this via `OffseasonRequired`. Confirm the endpoint exists and returns the dict the service produces. Add a brief Pydantic response model:

```python
class RolloverOut(BaseModel):
    from_season_id: int
    to_season_id: int
    new_year: int
    expired_player_count: int
```

- [ ] **Step 3: Frontend mutation**

```ts
// frontend/src/queries/season.ts
export function useRolloverSeason() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/season/start-next-season`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries(),
  });
}
```

(Use whatever the existing endpoint path is — confirm in `backend/app/api/season.py`.)

- [ ] **Step 4: Season-complete + offseason banner**

In `frontend/src/routes/season-complete.tsx`, add a "Start New Season" button visible when `phase === "offseason"`. Button calls `useRolloverSeason().mutate()`. After success, navigate to `/`.

In `frontend/src/routes/index.tsx`, render an offseason banner ("Offseason — start the next season") when `phase === "offseason"`, including the same Start-New-Season button. Optionally render a small "Expiring this offseason" list (skaters/goalies whose `contract.expires_after_year === season.year` and `team_id is not null`).

- [ ] **Step 5: Year indicator**

In `frontend/src/components/Shell.tsx`, add `Year {season.year}` somewhere in the header.

- [ ] **Step 6: Verify in browser**

Sim through a season into offseason; click Start New Season; verify dashboard now shows the new year, FA pool has new entrants, expired players are gone from rosters.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/season.py frontend/src/queries/season.ts frontend/src/routes/season-complete.tsx frontend/src/routes/index.tsx frontend/src/components/Shell.tsx
git commit -m "feat(fe): year + offseason banner + Start New Season"
```

---

## Task 19: Frontend — trade-block contract terms + NTC error

**Files:**
- Modify: `backend/app/schemas/trade.py` (expose contract on trade-block items)
- Modify: `backend/app/services/trade_service.py` (include contract in trade-block payload)
- Modify: `frontend/src/routes/trade-block.tsx`

- [ ] **Step 1: Expose contract on trade-block items**

In `backend/app/services/trade_service.py`, when building a trade-block entry dict, attach:

```python
"contract": {
    "length": c.length,
    "expires_after_year": c.expires_after_year,
    "salary": c.salary,
    "no_trade_clause": c.no_trade_clause,
} if c else None,
```

(`c` looked up via `contract_service.get_active_contract_for_*`.)

- [ ] **Step 2: Update Pydantic schema**

In `backend/app/schemas/trade.py`, add an optional `contract` field of the same shape (`ContractOut`).

- [ ] **Step 3: Render in frontend**

In `frontend/src/routes/trade-block.tsx`, add a column rendering `<ContractBadge contract={row.contract} currentYear={season.year} />`. On a 409 with code `NoTradeClause`, surface the message: `"Trade rejected: no-trade clause"`.

- [ ] **Step 4: Manual verify**

Open `/trade-block`, observe contract badges. (NTC holders are excluded so they shouldn't appear; you can flag-flip a contract via the API or psql to verify exclusion.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/trade.py backend/app/services/trade_service.py frontend/src/routes/trade-block.tsx
git commit -m "feat(fe): trade-block shows contract terms; surface NTC reason"
```

---

## Task 20: Integration test — full season → offseason → rollover → next season

**Files:**
- Create: `backend/tests/test_full_loop_with_contracts.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_full_loop_with_contracts.py
from app.models import Contract, Season, Skater
from app.services import contract_service
from app.services.advance_service import advance_matchday
from app.services.league_service import create_or_reset_league
from app.services.season_rollover_service import start_next_season


def test_full_loop_through_rollover(db):
    create_or_reset_league(db, seed=99)
    s0 = db.query(Season).order_by(Season.id.desc()).one()
    initial_contracts = db.query(Contract).filter_by(status="active").count()
    assert initial_contracts > 0

    # Sim until offseason.
    while True:
        res = advance_matchday(db)
        if res["season_phase"] == "offseason":
            break
        if res["season_status"] == "complete":
            raise AssertionError("season ended without entering offseason")

    # Rollover.
    start_next_season(db)

    s1 = db.query(Season).filter_by(status="active").one()
    assert s1.year == s0.year + 1
    assert s1.phase == "regular_season"

    # New season is playable.
    res = advance_matchday(db)
    assert res["season_phase"] == "regular_season"

    # Some contracts expired (those with length=1 signed at year=s0.year).
    expired = db.query(Contract).filter_by(status="expired").count()
    assert expired >= 1
```

- [ ] **Step 2: Run**

Run: `cd backend && pytest tests/test_full_loop_with_contracts.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_full_loop_with_contracts.py
git commit -m "test: full season → offseason → rollover integration"
```

---

## Task 21: Run the full backend suite + sanity-check frontend build

**Files:** none.

- [ ] **Step 1: Backend suite**

Run: `cd backend && pytest -v`
Expected: all pass. Investigate and fix any unrelated test that broke (likely `age` references in older tests).

- [ ] **Step 2: Frontend type-check + build**

Run: `cd frontend && npm run build`
Expected: clean build.

- [ ] **Step 3: Manual smoke**

Start backend + frontend, create a fresh league, advance through one season, perform a sign + release + propose-trade, hit offseason, click Start New Season, verify the new season is playable.

- [ ] **Step 4: Update docs**

Edit `docs/product-scope.md` to add a P1.3 section under Free Agents/Trades summarizing what shipped (mirror the format used for P1.1 / P1.2).

Edit `docs/not-now.md`: under Free Agency / Trades / Salary Cap / Waivers, note that Contracts (P1.3) are now implemented and reference the spec.

- [ ] **Step 5: Final commit**

```bash
git add docs/
git commit -m "docs: mark P1.3 contracts + season rollover shipped"
```

---

## Self-review notes (already applied)

**Spec coverage:** Every spec section maps to at least one task — data model (1–6), generation (7–10), sign FA (11–12), trade integration (13), offseason (14–15), UI (16–19), integration (20–21).

**Type consistency:** `length`, `salary`, `no_trade_clause` carry the same types from Pydantic body → service kwargs → ORM column. `season_year` is the consistent name for the contextual year argument across helpers (`age_from_birth_date(birth_date, season_year)`, `terminate_contract(..., season_year=...)`, `expire_contracts_through_year(new_season_year=...)`).

**Known soft spots a subagent should double-check during execution:**

1. **Test fixture `db_with_league`**: ensure it commits or flushes far enough that the partial unique index test in Task 8 surfaces the violation. If the savepoint pattern hides the integrity error, the test should call `db.commit()` between the two inserts.
2. **Existing test edits**: many tests reference `.age` directly. Search-replace `s.age` → `age_from_birth_date(s.birth_date, season.year)` before running each suite, not after.
3. **Pydantic `from_attributes=True` + computed age**: Task 12 chooses to feed dicts into Pydantic rather than auto-load from ORM rows because `age` is no longer a model attribute. Don't try to make this implicit via a SQLAlchemy hybrid — the spec explicitly forbids that.
4. **`_advance_playoffs` early-return paths**: confirm there's no other code path that sets `season.status = "complete"` for playoff completion — there's exactly one in the current implementation, but verify before editing.
