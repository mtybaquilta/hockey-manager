# Trade v2 — Offer Builder + AI Evaluation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the v1 trade-block / 1-for-1 propose flow with a multi-player offer builder backed by an AI evaluator, accessed via `POST /api/trades/evaluate` and `POST /api/trades/execute`.

**Architecture:** Pure-Python evaluation in `app/services/trade_eval.py` takes lists of `(player_type, player_id)` for both sides and returns an outlook (`accepted`, `outlook` enum, list of structured rejection reasons, side values). `trade_service.py` is rewritten to expose `evaluate_offer` and `execute_offer`; execute re-runs `evaluate_offer` inside the same transaction and only swaps `team_id`s if accepted. The old `/api/trade-block`, `/api/trades/propose`, and `/trade-block` UI are deleted. New `/trades` page lets the user pick a partner team and assemble 1–3 vs 1–3 offers.

**Tech Stack:** FastAPI + Pydantic + SQLAlchemy (backend), pytest (tests), React + TanStack Query + TanStack Router + Tailwind (frontend).

---

## Design Notes

### Value formula (per player, from the perspective of the receiving team)

```
value = ovr
      + age_modifier(age)                         # existing scale
      + position_need_modifier(receiving_team)    # existing scale (skater/goalie)
      + potential_modifier(potential, age)        # NEW
      + contender_modifier(receiving_team)        # NEW
      + round(contract_modifier)                  # existing
```

- `potential_modifier(p, age)`:
  - `age <= 23 and p >= 90` → +6
  - `age <= 23 and p >= 85` → +4
  - `age <= 25 and p >= 85` → +2
  - `age >= 30 and p < 80` → -1
  - else 0
- `contender_modifier(receiving_team)`: contender = team_avg_skater_ovr ≥ league_avg + 1.5; rebuilder = ≤ league_avg − 1.5; middle otherwise.
  - contender values present-skill: `+1` if `age <= 32`, `-2` if `age >= 33`.
  - rebuilder values youth: `+2` if `age <= 24`, `-2` if `age >= 30`.
  - middle: 0.

### Acceptance rules (multi-player)

Compute on the **AI partner's side** (i.e. value of what user offers to AI vs. value of what user requests):

```
offered_sum     = sum(value_for(p, receiving=ai_team)        for p in offered_by_user)
requested_sum   = sum(value_for(p, receiving=user_team)      for p in requested_from_ai)
package_penalty = max(0, len(offered) - len(requested)) * 3
best_offered    = max(value_for(p, receiving=ai_team)        for p in offered_by_user)
best_requested  = max(value_for(p, receiving=user_team)      for p in requested_from_ai)

accepted iff:
  offered_sum >= requested_sum + package_penalty
  AND best_offered >= best_requested - 5
  AND no rejection reason fires
```

### Rejection reasons (structured, deterministic)

Each is a `{code, message, player_type?, player_id?}`. Multiple may fire; all are returned.

- `NoTradeClause` — any player on either side has an active `no_trade_clause` contract.
- `RosterFloor` — post-trade, either team would have `< 12 skaters` or `< 1 goalie`.
- `TopProspect` — a requested AI player has `age <= 23 AND potential >= 85 AND ovr < 80`.
- `PositionNeedMismatch` — adding the offered package to AI team would push any single skater position to ≥ 6, **or** stripping the requested package would push AI below 1 player at any forward/D position the AI currently has ≥ 1 of.
- `ValueTooLow` — fired when sum/best-floor checks fail.

### Outlook enum (UI hint)

- `accept` — `accepted == true`
- `close` — `offered_sum >= requested_sum AND best_offered >= best_requested - 5` but `package_penalty` made it fail
- `reject` — otherwise

Roster warnings (non-blocking) are returned separately so the UI can flag them:
- `RosterBelowActiveFloor` (skaters < 18 or goalies < 2 on either side)
- `LineupSlotsCleared` (one or more players in either team's current lineup)

### Endpoint contract

```
POST /api/trades/evaluate
{
  "partner_team_id": int,
  "offered": [{"player_type":"skater","player_id":1}, ...]   # 1..3
  "requested": [{"player_type":"goalie","player_id":7}, ...] # 1..3
}
→ 200 EvaluateResponse {
  accepted: bool,
  outlook: "accept" | "close" | "reject",
  offered_value: int,
  requested_value: int,
  rejection_reasons: RejectionReason[],
  warnings: Warning[],
}

POST /api/trades/execute
(same body)
→ 200 ExecuteResponse {
  accepted: bool,
  outlook, offered_value, requested_value, rejection_reasons, warnings,   # mirrors evaluate
  acquired: [{player_type, player_id}],     # filled if accepted
  traded_away: [{player_type, player_id}],  # filled if accepted
}
```

`evaluate` never mutates. `execute` re-runs `evaluate_offer` inside the transaction; if not accepted, returns 200 with `accepted=false` and reasons (no DB write). If accepted, swaps `team_id` for all players, clears affected lineup slots on both teams, flushes.

Domain errors (still 4xx, raised before evaluation):
- `400 TradeOfferInvalid` — bad shape (empty side, > 3, duplicate ids, free agent referenced, offered side not on user team, requested side not on partner team).
- `403 NotUserTeam` — no manager profile / team set.
- `404 TeamNotFound` — partner team missing.
- `404 SkaterNotFound` / `404 GoalieNotFound` — referenced player missing.
- `409 SeasonAlreadyComplete` — season is complete.
- `422 TradeWithOwnTeamNotAllowed` — partner_team_id == user team.

### Things being deleted (v1 cleanup)

- Backend: `compute_trade_block`, `propose_trade`, `TradeOfferInvalid`, `TradeWithOwnTeamNotAllowed`, `TradeTargetNotAvailable` (we re-add Invalid/OwnTeamNotAllowed alongside new code), `GET /api/trade-block`, `POST /api/trades/propose`. Schemas `TradeBlockEntryOut`, `TradeProposalIn`, `TradeProposalOut`.
- Tests: `test_trade_block.py`, `test_trade_ntc.py`, `test_trade_api.py` (replaced by `test_trade_eval.py` + `test_trade_api.py` rewrite).
- Frontend: `routes/trade-block.tsx`, `queries/trades.ts` (rewritten), `TradeBlockEntry`/`TradeProposalRequest`/`TradeProposalResponse` types, the `trade-block` nav entry in `Shell.tsx`.

### Files

- Create: `backend/app/services/trade_eval.py` — pure(ish) evaluator: takes ORM-loaded players + season_year + db (for active contracts/team-context queries) and returns a typed result.
- Modify: `backend/app/services/trade_service.py` — replace v1 functions with `evaluate_offer` and `execute_offer`.
- Modify: `backend/app/schemas/trade.py` — replace v1 schemas with `OfferSide`, `EvaluateRequest`, `EvaluateResponse`, `ExecuteResponse`, `RejectionReason`, `Warning`.
- Modify: `backend/app/api/trades.py` — replace endpoints.
- Modify: `backend/app/errors.py` — keep `TradeOfferInvalid`, `TradeWithOwnTeamNotAllowed`; remove `TradeTargetNotAvailable` (defined in trade_service in v1 — not in errors.py — verify and skip if absent).
- Create: `backend/tests/test_trade_eval.py` — pure unit tests for evaluator.
- Modify (rewrite): `backend/tests/test_trade_api.py` — integration tests against new endpoints.
- Delete: `backend/tests/test_trade_block.py`, `backend/tests/test_trade_ntc.py`.
- Modify: `frontend/src/api/types.ts` — replace v1 types with v2 types.
- Rewrite: `frontend/src/queries/trades.ts` — `useEvaluateTrade`, `useExecuteTrade` mutations.
- Create: `frontend/src/routes/trades.tsx` — Offer Builder page.
- Delete: `frontend/src/routes/trade-block.tsx`.
- Modify: `frontend/src/components/Shell.tsx` — replace `trade-block` nav entry with `trades`.
- Regenerate: `frontend/src/routeTree.gen.ts` (auto via vite plugin).

---

## Task 1: Add v2 schemas (delete v1)

**Files:**
- Modify: `backend/app/schemas/trade.py`

- [ ] **Step 1: Replace file contents**

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PlayerType = Literal["skater", "goalie"]
Outlook = Literal["accept", "close", "reject"]


class OfferSidePlayer(BaseModel):
    player_type: PlayerType
    player_id: int


class RejectionReason(BaseModel):
    code: Literal[
        "ValueTooLow",
        "NoTradeClause",
        "PositionNeedMismatch",
        "TopProspect",
        "RosterFloor",
    ]
    message: str
    player_type: PlayerType | None = None
    player_id: int | None = None


class TradeWarning(BaseModel):
    code: Literal["RosterBelowActiveFloor", "LineupSlotsCleared"]
    message: str
    team_id: int | None = None


class EvaluateRequest(BaseModel):
    partner_team_id: int
    offered: list[OfferSidePlayer] = Field(min_length=1, max_length=3)
    requested: list[OfferSidePlayer] = Field(min_length=1, max_length=3)


class EvaluateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    accepted: bool
    outlook: Outlook
    offered_value: int
    requested_value: int
    rejection_reasons: list[RejectionReason]
    warnings: list[TradeWarning]


class AcquiredPlayer(BaseModel):
    player_type: PlayerType
    player_id: int


class ExecuteResponse(EvaluateResponse):
    acquired: list[AcquiredPlayer]
    traded_away: list[AcquiredPlayer]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/trade.py
git commit -m "feat(trade-v2): replace trade schemas with offer-builder shape"
```

---

## Task 2: Pure trade evaluator — value primitives

**Files:**
- Create: `backend/app/services/trade_eval.py`
- Create: `backend/tests/test_trade_eval.py`

- [ ] **Step 1: Write failing test for `age_modifier` and `potential_modifier`**

```python
# backend/tests/test_trade_eval.py
from app.services.trade_eval import age_modifier, potential_modifier


def test_age_modifier_brackets():
    assert age_modifier(20) == 4
    assert age_modifier(25) == 2
    assert age_modifier(29) == 0
    assert age_modifier(33) == -2
    assert age_modifier(36) == -5


def test_potential_modifier_young_high_potential():
    assert potential_modifier(potential=92, age=21) == 6
    assert potential_modifier(potential=86, age=22) == 4
    assert potential_modifier(potential=86, age=25) == 2
    assert potential_modifier(potential=78, age=31) == -1
    assert potential_modifier(potential=80, age=27) == 0
```

- [ ] **Step 2: Run; expect ImportError**

```bash
cd backend && pytest tests/test_trade_eval.py -x -q
```

Expected: collection error / ImportError.

- [ ] **Step 3: Implement primitives**

```python
# backend/app/services/trade_eval.py
"""Pure trade-evaluation primitives (no FastAPI; uses SQLAlchemy session for lookups)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.models import Goalie, Skater, Team


PlayerType = Literal["skater", "goalie"]


def age_modifier(age: int) -> int:
    if age <= 23:
        return 4
    if age <= 27:
        return 2
    if age <= 31:
        return 0
    if age <= 35:
        return -2
    return -5


def potential_modifier(potential: int, age: int) -> int:
    if age <= 23 and potential >= 90:
        return 6
    if age <= 23 and potential >= 85:
        return 4
    if age <= 25 and potential >= 85:
        return 2
    if age >= 30 and potential < 80:
        return -1
    return 0
```

- [ ] **Step 4: Run; expect pass**

```bash
cd backend && pytest tests/test_trade_eval.py -x -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/trade_eval.py backend/tests/test_trade_eval.py
git commit -m "feat(trade-v2): add age/potential value modifiers"
```

---

## Task 3: Contender / rebuilder classification

**Files:**
- Modify: `backend/app/services/trade_eval.py`
- Modify: `backend/tests/test_trade_eval.py`

- [ ] **Step 1: Write failing test**

```python
# Append to backend/tests/test_trade_eval.py
import pytest

from app.services.trade_eval import (
    classify_team_role,
    contender_modifier,
)


def test_contender_modifier_values_present_skill():
    assert contender_modifier("contender", age=27) == 1
    assert contender_modifier("contender", age=34) == -2
    assert contender_modifier("rebuilder", age=22) == 2
    assert contender_modifier("rebuilder", age=31) == -2
    assert contender_modifier("middle", age=27) == 0


def test_classify_team_role_uses_avg_skater_ovr(db, _league):
    # _league fixture creates the standard 4-team league; pick any team and verify
    # output is one of {contender, middle, rebuilder}. Deterministic per seed.
    teams = db.query(__import__("app.models", fromlist=["Team"]).Team).order_by(  # noqa
        __import__("app.models", fromlist=["Team"]).Team.id
    ).all()
    role = classify_team_role(db, teams[0].id)
    assert role in ("contender", "middle", "rebuilder")
```

Add a `_league` conftest hookup if not already there. (Existing `tests/conftest.py` already provides `db`; reuse `create_or_reset_league` directly inside the test if no `_league` fixture exists. Replace the test body with the inline form below if so:)

```python
def test_classify_team_role_uses_avg_skater_ovr(db):
    from app.services.league_service import create_or_reset_league
    from app.models import Team
    create_or_reset_league(db, seed=42)
    team_id = db.query(Team).order_by(Team.id).first().id
    role = classify_team_role(db, team_id)
    assert role in ("contender", "middle", "rebuilder")
```

- [ ] **Step 2: Run; expect failure**

```bash
cd backend && pytest tests/test_trade_eval.py -x -q
```

- [ ] **Step 3: Implement**

```python
# Append to backend/app/services/trade_eval.py
TeamRole = Literal["contender", "middle", "rebuilder"]


def _team_avg_skater_ovr(db: Session, team_id: int) -> float:
    from app.services.generation.players import skater_overall

    skaters = db.query(Skater).filter(Skater.team_id == team_id).all()
    if not skaters:
        return 0.0
    return sum(
        skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)
        for s in skaters
    ) / len(skaters)


def _league_avg_skater_ovr(db: Session) -> float:
    teams = db.query(Team).all()
    if not teams:
        return 0.0
    avgs = [_team_avg_skater_ovr(db, t.id) for t in teams]
    avgs = [a for a in avgs if a > 0]
    return sum(avgs) / len(avgs) if avgs else 0.0


def classify_team_role(db: Session, team_id: int) -> TeamRole:
    team_avg = _team_avg_skater_ovr(db, team_id)
    league_avg = _league_avg_skater_ovr(db)
    diff = team_avg - league_avg
    if diff >= 1.5:
        return "contender"
    if diff <= -1.5:
        return "rebuilder"
    return "middle"


def contender_modifier(role: TeamRole, age: int) -> int:
    if role == "contender":
        return 1 if age <= 32 else -2
    if role == "rebuilder":
        return 2 if age <= 24 else (-2 if age >= 30 else 0)
    return 0
```

- [ ] **Step 4: Run; expect pass**

```bash
cd backend && pytest tests/test_trade_eval.py -x -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/trade_eval.py backend/tests/test_trade_eval.py
git commit -m "feat(trade-v2): add contender/rebuilder team role classifier"
```

---

## Task 4: Position-need modifier and per-player value

**Files:**
- Modify: `backend/app/services/trade_eval.py`
- Modify: `backend/tests/test_trade_eval.py`

- [ ] **Step 1: Write failing test for value_skater + value_goalie**

```python
# Append to backend/tests/test_trade_eval.py
def test_value_skater_returns_int(db):
    from app.services.league_service import create_or_reset_league
    from app.models import Skater, Team
    from app.services.trade_eval import value_skater

    create_or_reset_league(db, seed=42)
    teams = db.query(Team).order_by(Team.id).all()
    src = teams[0]
    dst = teams[1]
    s = db.query(Skater).filter(Skater.team_id == src.id).first()
    v = value_skater(db, s, receiving_team_id=dst.id, season_year=db_year(db))
    assert isinstance(v, int)


def db_year(db):
    from app.models import Season
    return db.query(Season).order_by(Season.id.desc()).first().year


def test_value_goalie_returns_int(db):
    from app.services.league_service import create_or_reset_league
    from app.models import Goalie, Team
    from app.services.trade_eval import value_goalie

    create_or_reset_league(db, seed=42)
    teams = db.query(Team).order_by(Team.id).all()
    g = db.query(Goalie).filter(Goalie.team_id == teams[0].id).first()
    v = value_goalie(db, g, receiving_team_id=teams[1].id, season_year=db_year(db))
    assert isinstance(v, int)
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement**

```python
# Append to backend/app/services/trade_eval.py
from app.services import contract_service
from app.services.generation.contracts import market_salary
from app.services.generation.players import goalie_overall, skater_overall
from app.services.player_age import age_from_birth_date


CONTRACT_LENGTH_WEIGHT = 0.5
CONTRACT_SALARY_WEIGHT = 0.001


def _skater_ovr(s: Skater) -> int:
    return skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)


def _goalie_ovr(g: Goalie) -> int:
    return goalie_overall(g.reflexes, g.positioning, g.rebound_control, g.puck_handling, g.mental)


def _skater_position_need(db: Session, position: str, receiving_team_id: int) -> int:
    same = db.query(Skater).filter(
        Skater.team_id == receiving_team_id, Skater.position == position
    ).count()
    if same <= 1:
        return 3
    if same >= 5:
        return -3
    return 0


def _goalie_need(db: Session, receiving_team_id: int) -> int:
    n = db.query(Goalie).filter(Goalie.team_id == receiving_team_id).count()
    if n <= 1:
        return 3
    if n >= 4:
        return -3
    return 0


def _contract_modifier(
    db: Session, player_type: PlayerType, player_id: int, season_year: int, ovr: int
) -> float:
    if player_type == "skater":
        c = contract_service.get_active_contract_for_skater(db, player_id)
    else:
        c = contract_service.get_active_contract_for_goalie(db, player_id)
    if not c:
        return 0.0
    yrs = max(0, c.expires_after_year - season_year + 1)
    market = market_salary(ovr)
    return (yrs - 2) * CONTRACT_LENGTH_WEIGHT - (c.salary - market) * CONTRACT_SALARY_WEIGHT


def value_skater(db: Session, s: Skater, receiving_team_id: int, season_year: int) -> int:
    age = age_from_birth_date(s.birth_date, season_year)
    ovr = _skater_ovr(s)
    role = classify_team_role(db, receiving_team_id)
    return (
        ovr
        + age_modifier(age)
        + _skater_position_need(db, s.position, receiving_team_id)
        + potential_modifier(s.potential, age)
        + contender_modifier(role, age)
        + int(round(_contract_modifier(db, "skater", s.id, season_year, ovr)))
    )


def value_goalie(db: Session, g: Goalie, receiving_team_id: int, season_year: int) -> int:
    age = age_from_birth_date(g.birth_date, season_year)
    ovr = _goalie_ovr(g)
    role = classify_team_role(db, receiving_team_id)
    return (
        ovr
        + age_modifier(age)
        + _goalie_need(db, receiving_team_id)
        + potential_modifier(g.potential, age)
        + contender_modifier(role, age)
        + int(round(_contract_modifier(db, "goalie", g.id, season_year, ovr)))
    )
```

- [ ] **Step 4: Run; expect pass**

```bash
cd backend && pytest tests/test_trade_eval.py -x -q
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/trade_eval.py backend/tests/test_trade_eval.py
git commit -m "feat(trade-v2): per-player value w/ potential + contender/need modifiers"
```

---

## Task 5: Evaluate offer — input validation + result type

**Files:**
- Modify: `backend/app/services/trade_eval.py`
- Modify: `backend/app/services/trade_service.py` (rewrite)
- Modify: `backend/app/api/trades.py` (rewrite)
- Modify: `backend/tests/test_trade_eval.py`

- [ ] **Step 1: Add result dataclass + offer parsing in trade_eval**

```python
# Append to backend/app/services/trade_eval.py
@dataclass(frozen=True)
class OfferPlayer:
    player_type: PlayerType
    player_id: int


@dataclass
class RejectionReasonOut:
    code: str
    message: str
    player_type: PlayerType | None = None
    player_id: int | None = None


@dataclass
class WarningOut:
    code: str
    message: str
    team_id: int | None = None


@dataclass
class EvaluateOutcome:
    accepted: bool
    outlook: str  # "accept" | "close" | "reject"
    offered_value: int
    requested_value: int
    rejection_reasons: list[RejectionReasonOut]
    warnings: list[WarningOut]
```

- [ ] **Step 2: Wire trade_service to call evaluator (skeleton, returns reject for now)**

Replace contents of `backend/app/services/trade_service.py`:

```python
from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import (
    DomainError,
    GoalieNotFound,
    NoTradeClause,
    NotUserTeam,
    SeasonAlreadyComplete,
    SkaterNotFound,
    TeamNotFound,
)
from app.models import Goalie, Lineup, Season, Skater, Team
from app.services.free_agents_service import (
    _clear_goalie_from_lineup,
    _clear_skater_from_lineup,
    _current_user_team_id,
)
from app.services import trade_eval
from app.services.trade_eval import (
    EvaluateOutcome,
    OfferPlayer,
    RejectionReasonOut,
    WarningOut,
)


class TradeOfferInvalid(DomainError):
    code = "TradeOfferInvalid"
    status = 400


class TradeWithOwnTeamNotAllowed(DomainError):
    code = "TradeWithOwnTeamNotAllowed"
    status = 422


def _require_active_season(db: Session) -> Season:
    season = db.query(Season).order_by(Season.id.desc()).first()
    if season is None:
        raise NotUserTeam()
    if getattr(season, "status", None) == "complete":
        raise SeasonAlreadyComplete()
    return season


def _load_player(db: Session, p: OfferPlayer):
    if p.player_type == "skater":
        s = db.query(Skater).filter(Skater.id == p.player_id).first()
        if s is None:
            raise SkaterNotFound()
        return s
    g = db.query(Goalie).filter(Goalie.id == p.player_id).first()
    if g is None:
        raise GoalieNotFound()
    return g


def _validate_shape(
    db: Session,
    user_team_id: int,
    partner_team_id: int,
    offered: list[OfferPlayer],
    requested: list[OfferPlayer],
) -> None:
    if not (1 <= len(offered) <= 3) or not (1 <= len(requested) <= 3):
        raise TradeOfferInvalid("Each side must have 1–3 players.")
    seen: set[tuple[str, int]] = set()
    for p in (*offered, *requested):
        key = (p.player_type, p.player_id)
        if key in seen:
            raise TradeOfferInvalid("Duplicate player in offer.")
        seen.add(key)
    if db.query(Team).filter(Team.id == partner_team_id).first() is None:
        raise TeamNotFound()
    if partner_team_id == user_team_id:
        raise TradeWithOwnTeamNotAllowed()
    for p in offered:
        obj = _load_player(db, p)
        if obj.team_id != user_team_id:
            raise TradeOfferInvalid("Offered player must be on the user team.")
    for p in requested:
        obj = _load_player(db, p)
        if obj.team_id != partner_team_id:
            raise TradeOfferInvalid("Requested player must be on the partner team.")


def evaluate_offer(
    db: Session,
    partner_team_id: int,
    offered: list[OfferPlayer],
    requested: list[OfferPlayer],
) -> EvaluateOutcome:
    season = _require_active_season(db)
    user_team_id = _current_user_team_id(db)
    if user_team_id is None:
        raise NotUserTeam()
    _validate_shape(db, user_team_id, partner_team_id, offered, requested)
    return trade_eval.evaluate(
        db,
        season_year=season.year,
        user_team_id=user_team_id,
        partner_team_id=partner_team_id,
        offered=offered,
        requested=requested,
    )


def execute_offer(
    db: Session,
    partner_team_id: int,
    offered: list[OfferPlayer],
    requested: list[OfferPlayer],
) -> tuple[EvaluateOutcome, list[OfferPlayer], list[OfferPlayer]]:
    outcome = evaluate_offer(db, partner_team_id, offered, requested)
    if not outcome.accepted:
        return outcome, [], []
    user_team_id = _current_user_team_id(db)
    assert user_team_id is not None
    # Clear lineup slots and swap team_ids (mirrors release/v1 trade flow).
    for p in offered:
        if p.player_type == "skater":
            _clear_skater_from_lineup(db, user_team_id, p.player_id)
            db.query(Skater).filter(Skater.id == p.player_id).update(
                {"team_id": partner_team_id}
            )
        else:
            _clear_goalie_from_lineup(db, user_team_id, p.player_id)
            db.query(Goalie).filter(Goalie.id == p.player_id).update(
                {"team_id": partner_team_id}
            )
    for p in requested:
        if p.player_type == "skater":
            _clear_skater_from_lineup(db, partner_team_id, p.player_id)
            db.query(Skater).filter(Skater.id == p.player_id).update(
                {"team_id": user_team_id}
            )
        else:
            _clear_goalie_from_lineup(db, partner_team_id, p.player_id)
            db.query(Goalie).filter(Goalie.id == p.player_id).update(
                {"team_id": user_team_id}
            )
    db.flush()
    return outcome, list(requested), list(offered)
```

- [ ] **Step 3: Stub `trade_eval.evaluate` to return reject**

Append to `trade_eval.py`:

```python
def evaluate(
    db: Session,
    season_year: int,
    user_team_id: int,
    partner_team_id: int,
    offered: list[OfferPlayer],
    requested: list[OfferPlayer],
) -> EvaluateOutcome:
    return EvaluateOutcome(
        accepted=False,
        outlook="reject",
        offered_value=0,
        requested_value=0,
        rejection_reasons=[],
        warnings=[],
    )
```

- [ ] **Step 4: Replace `backend/app/api/trades.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.trade import (
    AcquiredPlayer,
    EvaluateRequest,
    EvaluateResponse,
    ExecuteResponse,
    RejectionReason,
    TradeWarning,
)
from app.services import trade_service as svc
from app.services.trade_eval import OfferPlayer

router = APIRouter(tags=["trades"])


def _to_offer(items) -> list[OfferPlayer]:
    return [OfferPlayer(player_type=i.player_type, player_id=i.player_id) for i in items]


def _outcome_to_response(o) -> dict:
    return {
        "accepted": o.accepted,
        "outlook": o.outlook,
        "offered_value": o.offered_value,
        "requested_value": o.requested_value,
        "rejection_reasons": [
            RejectionReason(code=r.code, message=r.message, player_type=r.player_type, player_id=r.player_id)
            for r in o.rejection_reasons
        ],
        "warnings": [
            TradeWarning(code=w.code, message=w.message, team_id=w.team_id)
            for w in o.warnings
        ],
    }


@router.post("/trades/evaluate", response_model=EvaluateResponse)
def evaluate_trade(payload: EvaluateRequest, db: Session = Depends(get_db)):
    outcome = svc.evaluate_offer(
        db,
        partner_team_id=payload.partner_team_id,
        offered=_to_offer(payload.offered),
        requested=_to_offer(payload.requested),
    )
    return _outcome_to_response(outcome)


@router.post("/trades/execute", response_model=ExecuteResponse)
def execute_trade(payload: EvaluateRequest, db: Session = Depends(get_db)):
    outcome, acquired, traded_away = svc.execute_offer(
        db,
        partner_team_id=payload.partner_team_id,
        offered=_to_offer(payload.offered),
        requested=_to_offer(payload.requested),
    )
    body = _outcome_to_response(outcome)
    body["acquired"] = [AcquiredPlayer(player_type=p.player_type, player_id=p.player_id) for p in acquired]
    body["traded_away"] = [AcquiredPlayer(player_type=p.player_type, player_id=p.player_id) for p in traded_away]
    return body
```

- [ ] **Step 5: Add validation test**

```python
# Append to backend/tests/test_trade_eval.py
def test_evaluate_offer_rejects_partner_equals_user(db):
    from app.services.league_service import create_or_reset_league
    from app.services import manager_profile_service, trade_service
    from app.services.trade_eval import OfferPlayer
    from app.services.trade_service import TradeWithOwnTeamNotAllowed
    from app.models import Skater, Team

    create_or_reset_league(db, seed=42)
    p = manager_profile_service.create_profile(db, name="Coach")
    t = db.query(Team).order_by(Team.id).first()
    manager_profile_service.set_team(db, p.id, t.id)
    db.flush()
    s1, s2 = db.query(Skater).filter(Skater.team_id == t.id).limit(2).all()
    import pytest
    with pytest.raises(TradeWithOwnTeamNotAllowed):
        trade_service.evaluate_offer(
            db,
            partner_team_id=t.id,
            offered=[OfferPlayer("skater", s1.id)],
            requested=[OfferPlayer("skater", s2.id)],
        )
```

- [ ] **Step 6: Run; expect pass**

```bash
cd backend && pytest tests/test_trade_eval.py -x -q
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/trade_eval.py backend/app/services/trade_service.py backend/app/api/trades.py backend/tests/test_trade_eval.py
git commit -m "feat(trade-v2): scaffold evaluate/execute endpoints + shape validation"
```

---

## Task 6: Implement core evaluation logic

**Files:**
- Modify: `backend/app/services/trade_eval.py`
- Modify: `backend/tests/test_trade_eval.py`

- [ ] **Step 1: Replace `evaluate` body in trade_eval.py**

```python
def evaluate(
    db: Session,
    season_year: int,
    user_team_id: int,
    partner_team_id: int,
    offered: list[OfferPlayer],
    requested: list[OfferPlayer],
) -> EvaluateOutcome:
    from app.services import contract_service

    def _resolve(p: OfferPlayer):
        if p.player_type == "skater":
            return db.query(Skater).filter(Skater.id == p.player_id).first()
        return db.query(Goalie).filter(Goalie.id == p.player_id).first()

    def _val(p: OfferPlayer, receiving_team_id: int) -> int:
        obj = _resolve(p)
        if p.player_type == "skater":
            return value_skater(db, obj, receiving_team_id, season_year)
        return value_goalie(db, obj, receiving_team_id, season_year)

    def _name(p: OfferPlayer) -> str:
        return _resolve(p).name

    def _ntc(p: OfferPlayer) -> bool:
        if p.player_type == "skater":
            c = contract_service.get_active_contract_for_skater(db, p.player_id)
        else:
            c = contract_service.get_active_contract_for_goalie(db, p.player_id)
        return bool(c and c.no_trade_clause)

    reasons: list[RejectionReasonOut] = []

    # NTC blocks regardless of value
    for p in (*offered, *requested):
        if _ntc(p):
            reasons.append(
                RejectionReasonOut(
                    code="NoTradeClause",
                    message=f"{_name(p)} has a no-trade clause.",
                    player_type=p.player_type,
                    player_id=p.player_id,
                )
            )

    # Top prospect: a *requested* AI player who is a young high-potential non-star
    for p in requested:
        if p.player_type != "skater":
            continue
        s = _resolve(p)
        age = age_from_birth_date(s.birth_date, season_year)
        ovr = _skater_ovr(s)
        if age <= 23 and s.potential >= 85 and ovr < 80:
            reasons.append(
                RejectionReasonOut(
                    code="TopProspect",
                    message=f"{s.name} is a top prospect — not available.",
                    player_type="skater",
                    player_id=p.player_id,
                )
            )

    # Roster floor (catastrophic) post-trade
    user_skaters = db.query(Skater).filter(Skater.team_id == user_team_id).count()
    user_goalies = db.query(Goalie).filter(Goalie.team_id == user_team_id).count()
    partner_skaters = db.query(Skater).filter(Skater.team_id == partner_team_id).count()
    partner_goalies = db.query(Goalie).filter(Goalie.team_id == partner_team_id).count()

    def _delta(side, kind):
        return sum(1 for p in side if p.player_type == kind)

    user_skaters_after = user_skaters - _delta(offered, "skater") + _delta(requested, "skater")
    user_goalies_after = user_goalies - _delta(offered, "goalie") + _delta(requested, "goalie")
    partner_skaters_after = partner_skaters + _delta(offered, "skater") - _delta(requested, "skater")
    partner_goalies_after = partner_goalies + _delta(offered, "goalie") - _delta(requested, "goalie")

    if user_skaters_after < 12 or partner_skaters_after < 12:
        reasons.append(RejectionReasonOut(code="RosterFloor", message="Not enough skaters post-trade."))
    if user_goalies_after < 1 or partner_goalies_after < 1:
        reasons.append(RejectionReasonOut(code="RosterFloor", message="Not enough goalies post-trade."))

    # Position need mismatch (one direction: AI overload at any single skater position)
    pos_after_partner: dict[str, int] = {}
    rows = db.query(Skater.position).filter(Skater.team_id == partner_team_id).all()
    for (pos,) in rows:
        pos_after_partner[pos] = pos_after_partner.get(pos, 0) + 1
    for p in offered:
        if p.player_type == "skater":
            s = _resolve(p)
            pos_after_partner[s.position] = pos_after_partner.get(s.position, 0) + 1
    for p in requested:
        if p.player_type == "skater":
            s = _resolve(p)
            pos_after_partner[s.position] = pos_after_partner.get(s.position, 0) - 1
    for pos, n in pos_after_partner.items():
        if n >= 6:
            reasons.append(
                RejectionReasonOut(
                    code="PositionNeedMismatch",
                    message=f"Partner team would have too many at {pos}.",
                )
            )
            break

    # Value comparison
    offered_values = [_val(p, partner_team_id) for p in offered]
    requested_values = [_val(p, user_team_id) for p in requested]
    offered_sum = sum(offered_values)
    requested_sum = sum(requested_values)
    package_penalty = max(0, len(offered) - len(requested)) * 3
    best_offered = max(offered_values) if offered_values else 0
    best_requested = max(requested_values) if requested_values else 0

    sum_ok = offered_sum >= requested_sum + package_penalty
    floor_ok = best_offered >= best_requested - 5

    if not (sum_ok and floor_ok):
        reasons.append(
            RejectionReasonOut(
                code="ValueTooLow",
                message="Value too low for partner to accept.",
            )
        )

    # Outlook
    if not reasons:
        outlook = "accept"
        accepted = True
    else:
        only_value = all(r.code == "ValueTooLow" for r in reasons)
        close = (
            only_value
            and offered_sum >= requested_sum
            and best_offered >= best_requested - 5
        )
        outlook = "close" if close else "reject"
        accepted = False

    # Warnings (non-blocking)
    warnings: list[WarningOut] = []
    if user_skaters_after < 18 or user_goalies_after < 2:
        warnings.append(
            WarningOut(
                code="RosterBelowActiveFloor",
                message="Your roster will be below the active floor (18 skaters / 2 goalies).",
                team_id=user_team_id,
            )
        )
    if partner_skaters_after < 18 or partner_goalies_after < 2:
        warnings.append(
            WarningOut(
                code="RosterBelowActiveFloor",
                message="Partner roster will be below the active floor.",
                team_id=partner_team_id,
            )
        )

    # LineupSlotsCleared warning if any traded player is in their team's current lineup
    def _in_lineup(team_id: int, p: OfferPlayer) -> bool:
        lu = db.query(Lineup).filter(Lineup.team_id == team_id).first()
        if lu is None:
            return False
        cols = (
            ["line1_lw_id", "line1_c_id", "line1_rw_id",
             "line2_lw_id", "line2_c_id", "line2_rw_id",
             "line3_lw_id", "line3_c_id", "line3_rw_id",
             "line4_lw_id", "line4_c_id", "line4_rw_id",
             "pair1_ld_id", "pair1_rd_id",
             "pair2_ld_id", "pair2_rd_id",
             "pair3_ld_id", "pair3_rd_id"]
            if p.player_type == "skater"
            else ["starting_goalie_id", "backup_goalie_id"]
        )
        return any(getattr(lu, c) == p.player_id for c in cols)

    if any(_in_lineup(user_team_id, p) for p in offered) or any(
        _in_lineup(partner_team_id, p) for p in requested
    ):
        warnings.append(
            WarningOut(
                code="LineupSlotsCleared",
                message="Affected lineup slots will be cleared.",
            )
        )

    return EvaluateOutcome(
        accepted=accepted,
        outlook=outlook,
        offered_value=offered_sum,
        requested_value=requested_sum,
        rejection_reasons=reasons,
        warnings=warnings,
    )
```

Also import `Lineup` at top of `trade_eval.py`:

```python
from app.models import Goalie, Lineup, Skater, Team
```

- [ ] **Step 2: Add tests for evaluation logic**

```python
# Append to backend/tests/test_trade_eval.py
import pytest
from app.services.league_service import create_or_reset_league
from app.services import manager_profile_service, trade_service
from app.services.trade_eval import OfferPlayer
from app.models import Goalie, Skater, Team


def _setup_user(db, seed=42):
    create_or_reset_league(db, seed=seed)
    p = manager_profile_service.create_profile(db, name="Coach")
    t = db.query(Team).order_by(Team.id).first()
    manager_profile_service.set_team(db, p.id, t.id)
    db.flush()
    return t


def test_evaluate_skater_for_skater_returns_outlook(db):
    user_t = _setup_user(db)
    ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
    own = db.query(Skater).filter(Skater.team_id == user_t.id).order_by(Skater.id).first()
    target = db.query(Skater).filter(Skater.team_id == ai.id).order_by(Skater.id).first()
    out = trade_service.evaluate_offer(
        db, partner_team_id=ai.id,
        offered=[OfferPlayer("skater", own.id)],
        requested=[OfferPlayer("skater", target.id)],
    )
    assert out.outlook in ("accept", "close", "reject")


def test_ntc_blocks_evaluation(db):
    user_t = _setup_user(db)
    ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
    own = db.query(Skater).filter(Skater.team_id == user_t.id).first()
    target = db.query(Skater).filter(Skater.team_id == ai.id).first()
    from app.services import contract_service
    c = contract_service.get_active_contract_for_skater(db, target.id)
    c.no_trade_clause = True
    db.flush()
    out = trade_service.evaluate_offer(
        db, partner_team_id=ai.id,
        offered=[OfferPlayer("skater", own.id)],
        requested=[OfferPlayer("skater", target.id)],
    )
    assert not out.accepted
    assert any(r.code == "NoTradeClause" for r in out.rejection_reasons)
```

- [ ] **Step 3: Run; expect pass**

```bash
cd backend && pytest tests/test_trade_eval.py -x -q
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/trade_eval.py backend/tests/test_trade_eval.py
git commit -m "feat(trade-v2): implement evaluator with reasons + warnings"
```

---

## Task 7: API integration tests for evaluate/execute

**Files:**
- Modify (rewrite): `backend/tests/test_trade_api.py`
- Delete: `backend/tests/test_trade_block.py`, `backend/tests/test_trade_ntc.py`

- [ ] **Step 1: Delete v1 tests**

```bash
rm backend/tests/test_trade_block.py backend/tests/test_trade_ntc.py
```

- [ ] **Step 2: Write new api tests**

Replace `backend/tests/test_trade_api.py` with:

```python
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models import Goalie, Lineup, Season, Skater, Team
from app.services import manager_profile_service
from app.services.league_service import create_or_reset_league


def _client(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def _setup(db, seed=42):
    create_or_reset_league(db, seed=seed)
    p = manager_profile_service.create_profile(db, name="Coach")
    t = db.query(Team).order_by(Team.id).first()
    manager_profile_service.set_team(db, p.id, t.id)
    db.flush()
    return t


def test_evaluate_returns_outlook(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        own = db.query(Skater).filter(Skater.team_id == user_t.id).first()
        target = db.query(Skater).filter(Skater.team_id == ai.id).first()
        r = client.post("/api/trades/evaluate", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": own.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["outlook"] in ("accept", "close", "reject")
        assert "offered_value" in body and "requested_value" in body
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_execute_swaps_team_ids_when_accepted(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        # Pick a clearly under-asking AI skater + an over-valuing user skater of same position.
        ai_skaters = db.query(Skater).filter(Skater.team_id == ai.id).all()
        ai_skaters.sort(key=lambda s: s.shooting + s.skating + s.passing + s.defense + s.physical)
        target = ai_skaters[0]
        own_pool = db.query(Skater).filter(
            Skater.team_id == user_t.id, Skater.position == target.position
        ).all()
        own_pool.sort(key=lambda s: -(s.shooting + s.skating + s.passing + s.defense + s.physical))
        offered = own_pool[0]
        r = client.post("/api/trades/execute", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": offered.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        assert r.status_code == 200, r.text
        body = r.json()
        if body["accepted"]:
            db.expire_all()
            assert db.get(Skater, target.id).team_id == user_t.id
            assert db.get(Skater, offered.id).team_id == ai.id
            assert {(a["player_type"], a["player_id"]) for a in body["acquired"]} == {("skater", target.id)}
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_execute_does_not_mutate_when_rejected(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        # Strong AI target + weak user offer: very likely to be rejected.
        ai_skaters = db.query(Skater).filter(Skater.team_id == ai.id).all()
        ai_skaters.sort(key=lambda s: -(s.shooting + s.skating + s.passing + s.defense + s.physical))
        target = ai_skaters[0]
        own_pool = db.query(Skater).filter(
            Skater.team_id == user_t.id, Skater.position == target.position
        ).all()
        own_pool.sort(key=lambda s: s.shooting + s.skating + s.passing + s.defense + s.physical)
        weak = own_pool[0]
        r = client.post("/api/trades/execute", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": weak.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        assert r.status_code == 200
        body = r.json()
        if not body["accepted"]:
            db.expire_all()
            assert db.get(Skater, target.id).team_id == ai.id
            assert db.get(Skater, weak.id).team_id == user_t.id
            assert body["acquired"] == []
            assert body["traded_away"] == []
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_evaluate_partner_eq_user_team_rejected(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        s1, s2 = db.query(Skater).filter(Skater.team_id == user_t.id).limit(2).all()
        r = client.post("/api/trades/evaluate", json={
            "partner_team_id": user_t.id,
            "offered": [{"player_type": "skater", "player_id": s1.id}],
            "requested": [{"player_type": "skater", "player_id": s2.id}],
        })
        assert r.status_code == 422
        assert r.json()["error_code"] == "TradeWithOwnTeamNotAllowed"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_evaluate_blocked_when_season_complete(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        own = db.query(Skater).filter(Skater.team_id == user_t.id).first()
        target = db.query(Skater).filter(Skater.team_id == ai.id).first()
        s = db.query(Season).order_by(Season.id.desc()).first()
        s.status = "complete"
        db.flush()
        r = client.post("/api/trades/evaluate", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": own.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        assert r.status_code == 409
        assert r.json()["error_code"] == "SeasonAlreadyComplete"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_execute_clears_lineup_slots(db):
    user_t = _setup(db)
    try:
        client = _client(db)
        ai = db.query(Team).filter(Team.id != user_t.id).order_by(Team.id).first()
        ai_skaters = db.query(Skater).filter(Skater.team_id == ai.id).all()
        ai_skaters.sort(key=lambda s: s.shooting + s.skating + s.passing + s.defense + s.physical)
        target = ai_skaters[0]
        own_pool = db.query(Skater).filter(
            Skater.team_id == user_t.id, Skater.position == target.position
        ).all()
        own_pool.sort(key=lambda s: -(s.shooting + s.skating + s.passing + s.defense + s.physical))
        offered = own_pool[0]
        r = client.post("/api/trades/execute", json={
            "partner_team_id": ai.id,
            "offered": [{"player_type": "skater", "player_id": offered.id}],
            "requested": [{"player_type": "skater", "player_id": target.id}],
        })
        if r.json().get("accepted"):
            db.expire_all()
            ai_lu = db.query(Lineup).filter(Lineup.team_id == ai.id).first()
            user_lu = db.query(Lineup).filter(Lineup.team_id == user_t.id).first()
            cols = [c.name for c in ai_lu.__table__.columns if c.name.endswith("_id") and c.name != "team_id"]
            assert all(getattr(ai_lu, c) != target.id for c in cols)
            assert all(getattr(user_lu, c) != offered.id for c in cols)
    finally:
        app.dependency_overrides.pop(get_db, None)
```

- [ ] **Step 3: Run; expect pass**

```bash
cd backend && pytest tests/test_trade_api.py tests/test_trade_eval.py -x -q
```

- [ ] **Step 4: Run full suite to catch other regressions**

```bash
cd backend && pytest -x -q
```

Expected: pass. If any test refers to deleted v1 endpoints, fix or delete it.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_trade_api.py
git rm backend/tests/test_trade_block.py backend/tests/test_trade_ntc.py
git commit -m "test(trade-v2): replace v1 trade tests with evaluate/execute coverage"
```

---

## Task 8: Frontend types + queries

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify (rewrite): `frontend/src/queries/trades.ts`

- [ ] **Step 1: Replace trade types in `frontend/src/api/types.ts`**

Remove `TradeBlockEntry`, `TradeProposalRequest`, `TradeProposalResponse`. Add:

```ts
export interface TradeOfferPlayer { player_type: PlayerKind; player_id: number; }

export type TradeOutlook = "accept" | "close" | "reject";
export type TradeRejectionCode =
  | "ValueTooLow"
  | "NoTradeClause"
  | "PositionNeedMismatch"
  | "TopProspect"
  | "RosterFloor";
export type TradeWarningCode = "RosterBelowActiveFloor" | "LineupSlotsCleared";

export interface TradeRejectionReason {
  code: TradeRejectionCode;
  message: string;
  player_type?: PlayerKind | null;
  player_id?: number | null;
}
export interface TradeWarning {
  code: TradeWarningCode;
  message: string;
  team_id?: number | null;
}

export interface TradeEvaluateRequest {
  partner_team_id: number;
  offered: TradeOfferPlayer[];
  requested: TradeOfferPlayer[];
}
export interface TradeEvaluateResponse {
  accepted: boolean;
  outlook: TradeOutlook;
  offered_value: number;
  requested_value: number;
  rejection_reasons: TradeRejectionReason[];
  warnings: TradeWarning[];
}
export interface TradeExecuteResponse extends TradeEvaluateResponse {
  acquired: TradeOfferPlayer[];
  traded_away: TradeOfferPlayer[];
}
```

- [ ] **Step 2: Replace `frontend/src/queries/trades.ts`**

```ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type {
  TradeEvaluateRequest,
  TradeEvaluateResponse,
  TradeExecuteResponse,
} from "../api/types";

export const useEvaluateTrade = () =>
  useMutation({
    mutationFn: (req: TradeEvaluateRequest) =>
      api.post<TradeEvaluateResponse>("/api/trades/evaluate", req),
  });

export const useExecuteTrade = (userTeamId: number | null, partnerTeamId: number | null) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: TradeEvaluateRequest) =>
      api.post<TradeExecuteResponse>("/api/trades/execute", req),
    onSuccess: (res) => {
      if (!res.accepted) return;
      qc.invalidateQueries({ queryKey: ["teams"] });
      qc.invalidateQueries({ queryKey: ["roster"] });
      qc.invalidateQueries({ queryKey: ["lineup"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      if (userTeamId != null) {
        qc.invalidateQueries({ queryKey: ["team", userTeamId] });
        qc.invalidateQueries({ queryKey: ["lineup", userTeamId] });
        qc.invalidateQueries({ queryKey: ["roster", userTeamId] });
      }
      if (partnerTeamId != null) {
        qc.invalidateQueries({ queryKey: ["team", partnerTeamId] });
        qc.invalidateQueries({ queryKey: ["lineup", partnerTeamId] });
        qc.invalidateQueries({ queryKey: ["roster", partnerTeamId] });
      }
    },
  });
};
```

- [ ] **Step 3: Verify typecheck**

```bash
cd frontend && npm run typecheck 2>&1 | tail -40
```

Expected: only complaints from `routes/trade-block.tsx` (deleted in next task) and `Shell.tsx` nav id.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/queries/trades.ts
git commit -m "feat(trade-v2): frontend types + evaluate/execute query hooks"
```

---

## Task 9: New /trades route — Offer Builder UI

**Files:**
- Create: `frontend/src/routes/trades.tsx`
- Delete: `frontend/src/routes/trade-block.tsx`
- Modify: `frontend/src/components/Shell.tsx` (replace nav entry)

- [ ] **Step 1: Delete old route**

```bash
rm frontend/src/routes/trade-block.tsx
```

- [ ] **Step 2: Update Shell nav**

In `frontend/src/components/Shell.tsx` line 16, replace the `trade-block` nav entry with:

```tsx
  { id: "trades", label: "Trades", to: "/trades", icon: "M7 7h11l-3-3M17 17H6l3 3", match: (p) => p.startsWith("/trades") },
```

- [ ] **Step 3: Create `/trades` page**

```tsx
// frontend/src/routes/trades.tsx
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";

import { Button } from "../components/Button";
import { Shell } from "../components/Shell";
import { Table, Td, Th } from "../components/Table";
import { skaterOvr } from "../lib/roster-tags";
import { attrClass } from "../lib/team-colors";
import type {
  PlayerKind,
  TradeEvaluateResponse,
  TradeExecuteResponse,
  TradeOfferPlayer,
} from "../api/types";
import { useLeague } from "../queries/league";
import { useTeams, useRoster } from "../queries/teams";
import { useEvaluateTrade, useExecuteTrade } from "../queries/trades";

const goalieOvr = (g: { reflexes: number; positioning: number; rebound_control: number; puck_handling: number; mental: number }) =>
  Math.round(0.3 * g.reflexes + 0.25 * g.positioning + 0.2 * g.rebound_control + 0.15 * g.puck_handling + 0.1 * g.mental);

const SidePicker = ({
  title,
  roster,
  selected,
  onAdd,
  onRemove,
}: {
  title: string;
  roster: ReturnType<typeof useRoster>;
  selected: TradeOfferPlayer[];
  onAdd: (p: TradeOfferPlayer) => void;
  onRemove: (p: TradeOfferPlayer) => void;
}) => {
  const isSelected = (kind: PlayerKind, id: number) =>
    selected.some((s) => s.player_type === kind && s.player_id === id);

  return (
    <div className="card" style={{ padding: 12, minWidth: 320, flex: 1 }}>
      <div className="ribbon-h"><span className="accent" />{title} ({selected.length}/3)</div>
      {!roster.data ? (
        <div style={{ padding: 12, color: "var(--ink-3)" }}>Loading…</div>
      ) : (
        <Table>
          <thead>
            <tr><Th>Name</Th><Th>Pos</Th><Th className="num">OVR</Th><Th /></tr>
          </thead>
          <tbody>
            {roster.data.skaters.map((s) => {
              const sel = isSelected("skater", s.id);
              const ovr = skaterOvr(s);
              return (
                <tr key={`s${s.id}`}>
                  <Td>{s.name}</Td>
                  <Td style={{ color: "var(--ink-3)" }}>{s.position}</Td>
                  <Td className="num"><span className={`chip ovr ${attrClass(ovr)}`}>{ovr}</span></Td>
                  <Td>
                    <Button
                      variant={sel ? "ghost" : "default"}
                      disabled={!sel && selected.length >= 3}
                      onClick={() => sel
                        ? onRemove({ player_type: "skater", player_id: s.id })
                        : onAdd({ player_type: "skater", player_id: s.id })}
                    >
                      {sel ? "Remove" : "Add"}
                    </Button>
                  </Td>
                </tr>
              );
            })}
            {roster.data.goalies.map((g) => {
              const sel = isSelected("goalie", g.id);
              const ovr = goalieOvr(g);
              return (
                <tr key={`g${g.id}`}>
                  <Td>{g.name}</Td>
                  <Td style={{ color: "var(--ink-3)" }}>G</Td>
                  <Td className="num"><span className={`chip ovr ${attrClass(ovr)}`}>{ovr}</span></Td>
                  <Td>
                    <Button
                      variant={sel ? "ghost" : "default"}
                      disabled={!sel && selected.length >= 3}
                      onClick={() => sel
                        ? onRemove({ player_type: "goalie", player_id: g.id })
                        : onAdd({ player_type: "goalie", player_id: g.id })}
                    >
                      {sel ? "Remove" : "Add"}
                    </Button>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </div>
  );
};

const OutlookBadge = ({ outlook }: { outlook: "accept" | "close" | "reject" }) => {
  const color = outlook === "accept" ? "#1B6F43" : outlook === "close" ? "#A57400" : "#A1192A";
  const label = outlook === "accept" ? "Will accept" : outlook === "close" ? "Close" : "Will reject";
  return <span style={{ color, fontWeight: 700 }}>{label}</span>;
};

const TradesPage = () => {
  const league = useLeague();
  const teams = useTeams();
  const userTeamId = league.data?.user_team_id ?? null;
  const aiTeams = useMemo(
    () => (teams.data ?? []).filter((t) => t.id !== userTeamId),
    [teams.data, userTeamId],
  );
  const [partnerId, setPartnerId] = useState<number | null>(null);
  useEffect(() => {
    if (partnerId == null && aiTeams.length > 0) setPartnerId(aiTeams[0].id);
  }, [aiTeams, partnerId]);

  const userRoster = useRoster(userTeamId ?? 0);
  const partnerRoster = useRoster(partnerId ?? 0);

  const [offered, setOffered] = useState<TradeOfferPlayer[]>([]);
  const [requested, setRequested] = useState<TradeOfferPlayer[]>([]);
  const [outlook, setOutlook] = useState<TradeEvaluateResponse | null>(null);
  const [submitMsg, setSubmitMsg] = useState<string | null>(null);

  const evalMut = useEvaluateTrade();
  const execMut = useExecuteTrade(userTeamId, partnerId);

  const resetSelections = () => {
    setOffered([]);
    setRequested([]);
    setOutlook(null);
    setSubmitMsg(null);
  };

  useEffect(() => { resetSelections(); }, [partnerId]);

  useEffect(() => {
    setSubmitMsg(null);
    if (userTeamId == null || partnerId == null || offered.length === 0 || requested.length === 0) {
      setOutlook(null);
      return;
    }
    evalMut.mutate(
      { partner_team_id: partnerId, offered, requested },
      { onSuccess: (res) => setOutlook(res), onError: () => setOutlook(null) },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(offered), JSON.stringify(requested), partnerId, userTeamId]);

  const submit = () => {
    if (userTeamId == null || partnerId == null) return;
    setSubmitMsg(null);
    execMut.mutate(
      { partner_team_id: partnerId, offered, requested },
      {
        onSuccess: (res: TradeExecuteResponse) => {
          if (res.accepted) {
            setSubmitMsg(`Trade accepted. Acquired ${res.acquired.length} player(s).`);
            resetSelections();
          } else {
            setSubmitMsg("Trade rejected.");
            setOutlook(res);
          }
        },
        onError: (err: unknown) => {
          const m = err instanceof Error ? err.message : "Trade failed.";
          setSubmitMsg(m);
        },
      },
    );
  };

  if (userTeamId == null) {
    return <Shell crumbs={["Trades"]}><div className="card" style={{ padding: 16 }}>Choose a team first.</div></Shell>;
  }

  return (
    <Shell crumbs={["Continental Hockey League", "Trades"]}>
      <div className="section-h">
        <h1>Trades</h1>
        <span className="sub">Build an offer (1–3 vs 1–3) and see how the partner reacts</span>
      </div>

      <div className="card" style={{ padding: 12, marginBottom: 14 }}>
        <label style={{ marginRight: 8, fontWeight: 600 }}>Trade partner:</label>
        <select value={partnerId ?? ""} onChange={(e) => setPartnerId(e.target.value ? Number(e.target.value) : null)}>
          {aiTeams.map((t) => (
            <option key={t.id} value={t.id}>{t.name} ({t.abbreviation})</option>
          ))}
        </select>
      </div>

      <div style={{ display: "flex", gap: 14, alignItems: "stretch", flexWrap: "wrap" }}>
        <SidePicker
          title="You give"
          roster={userRoster}
          selected={offered}
          onAdd={(p) => setOffered((s) => [...s, p])}
          onRemove={(p) => setOffered((s) => s.filter((x) => !(x.player_type === p.player_type && x.player_id === p.player_id)))}
        />
        <SidePicker
          title="You get"
          roster={partnerRoster}
          selected={requested}
          onAdd={(p) => setRequested((s) => [...s, p])}
          onRemove={(p) => setRequested((s) => s.filter((x) => !(x.player_type === p.player_type && x.player_id === p.player_id)))}
        />
      </div>

      <div className="card" style={{ padding: 12, marginTop: 14 }}>
        <div className="ribbon-h"><span className="accent" />Outlook</div>
        {!outlook ? (
          <div style={{ padding: 12, color: "var(--ink-3)" }}>
            {evalMut.isPending ? "Evaluating…" : "Add at least one player to each side to see the outlook."}
          </div>
        ) : (
          <div style={{ padding: 12 }}>
            <div style={{ marginBottom: 8 }}>
              <OutlookBadge outlook={outlook.outlook} />
              <span style={{ marginLeft: 12, color: "var(--ink-3)" }}>
                offered value <b>{outlook.offered_value}</b> · requested value <b>{outlook.requested_value}</b>
              </span>
            </div>
            {outlook.rejection_reasons.length > 0 && (
              <ul style={{ marginTop: 4 }}>
                {outlook.rejection_reasons.map((r, i) => (
                  <li key={i} style={{ color: "#A1192A" }}>{r.code}: {r.message}</li>
                ))}
              </ul>
            )}
            {outlook.warnings.length > 0 && (
              <ul style={{ marginTop: 4 }}>
                {outlook.warnings.map((w, i) => (
                  <li key={i} style={{ color: "#A57400" }}>{w.message}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        <div style={{ display: "flex", gap: 8, padding: 12 }}>
          <Button
            variant="primary"
            disabled={!outlook?.accepted || execMut.isPending}
            onClick={submit}
          >
            {execMut.isPending ? "Submitting…" : "Submit Trade"}
          </Button>
          <Button variant="ghost" onClick={resetSelections}>Clear</Button>
          {submitMsg && <span style={{ alignSelf: "center", fontWeight: 700 }}>{submitMsg}</span>}
        </div>
      </div>
    </Shell>
  );
};

export const Route = createFileRoute("/trades")({ component: TradesPage });
```

- [ ] **Step 4: Run dev typecheck**

```bash
cd frontend && npm run typecheck 2>&1 | tail -30
```

Expected: pass. If `routeTree.gen.ts` references the deleted `/trade-block`, run the dev server briefly to regenerate it, or run the route generator command (TanStack Router auto-regens on `npm run dev`). Then re-typecheck.

- [ ] **Step 5: Manual UI smoke**

```bash
cd frontend && npm run dev
```

Open the app, navigate to **Trades** in the sidebar:
- Select a partner; both rosters render.
- Add 1 player to each side → outlook appears within ~500 ms.
- Try a clearly under-value offer (worst skater for best skater) → expect `reject` with `ValueTooLow`.
- Try a clearly fair offer (top user skater for bottom AI skater of same position) → expect `accept`.
- Submit accepted trade → roster updates, banner shows acquired count, page resets.

Report any console errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/trades.tsx frontend/src/components/Shell.tsx frontend/src/routeTree.gen.ts
git rm frontend/src/routes/trade-block.tsx
git commit -m "feat(trade-v2): /trades offer builder page; remove /trade-block"
```

---

## Task 10: Final verification

- [ ] **Step 1: Backend full suite**

```bash
cd backend && pytest -x -q
```

Expected: all green. Investigate and fix any failures (most likely callers of the deleted v1 functions).

- [ ] **Step 2: Frontend typecheck + build**

```bash
cd frontend && npm run typecheck && npm run build
```

Expected: clean.

- [ ] **Step 3: Update product-scope + not-now**

In `docs/product-scope.md`, replace the **Trades (P1.2)** section with a brief P1.5 note:

```markdown
### Trades (P1.5)

- `/trades` page: offer builder with 1–3 players per side, AI partner selector, real-time evaluation outlook, and submit.
- `POST /api/trades/evaluate` and `POST /api/trades/execute`. Execute re-evaluates inside the transaction and only mutates if accepted.
- Value formula: OVR + age + position need + potential + contender/rebuilder + contract.
- Acceptance: sum-of-values + asymmetric package penalty + best-player floor.
- Structured rejection reasons: `ValueTooLow`, `NoTradeClause`, `PositionNeedMismatch`, `TopProspect`, `RosterFloor`. Non-blocking warnings: `RosterBelowActiveFloor`, `LineupSlotsCleared`.
- Out of scope (still): salary cap, draft picks, retained salary, multi-team trades, trade deadline, AI-initiated trades, negotiation rounds.
```

In `docs/not-now.md`, update the Trades line:

```markdown
- Trades (P1.2 → P1.5 implemented — multi-player offer builder + AI evaluation. Deferred: salary cap, draft picks, retained salary, multi-team, AI↔AI trades, deadline, negotiation rounds.)
```

- [ ] **Step 4: Commit + summary**

```bash
git add docs/product-scope.md docs/not-now.md
git commit -m "docs(trade-v2): document P1.5 trade offer builder + scope updates"
```

---

## Self-Review Notes

- **Spec coverage:** offer builder ✓, evaluate ✓, execute (re-runs eval) ✓, value formula (OVR/potential/age/position/contract/needs/contender) ✓, NTC blocked ✓, all rejection reasons ✓, post-accept team_id swap + lineup clear + invalidation ✓, /trades page ✓, partner selector ✓, add/remove ✓, outlook + reasons ✓, submit ✓. Out-of-scope items intentionally untouched.
- **Placeholders:** none — every code step is concrete.
- **Type consistency:** `OfferPlayer` (Python) ↔ `TradeOfferPlayer` (TS) align on `{player_type, player_id}`. `EvaluateOutcome` fields ↔ `EvaluateResponse`/`ExecuteResponse` fields align. `outlook` enum identical on both sides.
