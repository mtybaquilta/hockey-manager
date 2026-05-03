# Trade Block P1.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Constrained user-team-only 1-for-1 trade system. User browses computed trade-block players from AI teams and proposes single-player offers; backend evaluates deterministically and on accept swaps `team_id` in one transaction.

**Architecture:** Computed trade block (no new tables, no migration). Ownership = `team_id`; trade = swap. Same-type only (skater↔skater, goalie↔goalie). Existing services-only pattern (no new repositories layer). Reuses `skater_overall`/`goalie_overall` from `app.services.generation.players`. New errors live inside `trade_service.py` (matches `PlayerNotFreeAgent` pattern in `free_agents_service.py`).

**Tech Stack:** FastAPI / SQLAlchemy / Pydantic (backend); React + TanStack Router/Query + Tailwind (frontend).

---

## File structure

**Backend (new):**
- `backend/app/services/trade_service.py` — block computation, proposal evaluation, swap.
- `backend/app/schemas/trade.py` — `TradeBlockEntryOut`, `TradeProposalIn`, `TradeProposalOut`.
- `backend/app/api/trades.py` — `GET /api/trade-block`, `POST /api/trades/propose`.
- `backend/tests/test_trade_block.py` — block computation tests.
- `backend/tests/test_trade_api.py` — API + propose tests.

**Backend (modify):**
- `backend/app/api/__init__.py` — register `trades.router`.
- `docs/not-now.md` — annotate "Trades" entry with P1.2 implemented note.
- `docs/product-scope.md` — add Trades section under Phase 1 in-scope items.

**Frontend (new):**
- `frontend/src/queries/trades.ts` — `useTradeBlock`, `useProposeTrade`.
- `frontend/src/routes/trade-block.tsx` — page + offer panel.

**Frontend (modify):**
- `frontend/src/api/types.ts` — `TradeBlockEntry`, `TradeProposalRequest`, `TradeProposalResponse`.
- `frontend/src/components/Shell.tsx` — add Trade Block nav entry.
- `frontend/src/routeTree.gen.ts` — auto-regenerated.

---

## Pattern conformance (verified against existing code)

| Concern | Existing pattern | Plan conforms |
|---|---|---|
| Domain errors | `DomainError(code, status)`; service-specific errors live IN the service file (e.g. `PlayerNotFreeAgent` in `free_agents_service.py`) | Yes — trade errors in `trade_service.py` |
| OVR helper | `skater_overall(skating, shooting, passing, defense, physical)`, `goalie_overall(reflexes, positioning, rebound_control, puck_handling, mental)` already exported from `app.services.generation.players` | Reuse — no new module |
| Schema naming | `*Out` for responses, `*In` for requests; `model_config = ConfigDict(from_attributes=True)`; `computed_field` for derived OVR | Yes |
| Router registration | Add to `api/__init__.py` import block + include tuple | Yes |
| Service `_current_user_team_id` helper | Defined inline in `gameplan_service.py` and `free_agents_service.py` | Reuse pattern (import or duplicate locally — duplicate is fine, project already does this) |
| Lineup column constants | `SKATER_LINEUP_COLS` / `GOALIE_LINEUP_COLS` already exported by `free_agents_service.py` | Import from there |
| FE query keys | `["teams"]`, `["team", id]`, `["team", id, "roster"]`, `["lineup", teamId]` | Use `["trade-block"]` + invalidate the team/lineup keys above |
| FE route file | `routes/free-agents.tsx` style: filters at top, table card below, mutation hooks inline | Match |

---

## Domain rules

**Eligibility for the trade block (per AI team):**
1. Player belongs to that team (team_id != null, team_id != user_team_id).
2. **Exclude top core**: top 3 forwards by OVR + top 2 defensemen by OVR + #1 goalie by OVR.
3. **Exclude active-lineup players** (any id appearing in that team's `Lineup` row across `SKATER_LINEUP_COLS`/`GOALIE_LINEUP_COLS`).
4. From the remaining pool, rank by `block_score = age + (team_avg_skater_ovr − p.ovr)` for skaters, and analogously for goalies. Higher score = more likely on the block.
5. Take **up to 3 candidates per team**, minimum 0.
6. **Reason label** assigned by which factor dominated:
   - age ≥ 32 → `"Veteran available"`
   - else if (team_avg_ovr − p.ovr) ≥ 5 → `"Depth surplus"`
   - else if position has ≥ 4 same-position players (skater) → `"Position surplus"`
   - else → `"On the block"`

**Trade value:**
```
value(p) = ovr(p) + age_modifier(p.age) + position_need_modifier(p, receiving_team)
```
- Age modifier: 18-23 → +4, 24-27 → +2, 28-31 → 0, 32-35 → -2, 36+ → -5.
- Position need modifier:
  - Skater: receiving team count of `p.position` — ≤1 → +3, ≥5 → -3, else 0.
  - Goalie: receiving team goalie count — ≤1 → +3, ≥4 → -3, else 0.

**Acceptance:** `accept ⇔ offered_value >= target_value`. Pure deterministic; no RNG in P1.2.

**Hard rejections (any one fails → reject before value computation):**
- `SeasonAlreadyComplete` if season status complete.
- `NotUserTeam` (or `TradeWithOwnTeamNotAllowed`) if user_team_id is None or target.team_id == user_team_id.
- `SkaterNotFound`/`GoalieNotFound` if either id missing.
- `TradeOfferInvalid` if cross-type, or if offered.team_id != user_team_id, or if either player has team_id == null (free agent).
- `TradeTargetNotAvailable` if target not in current `compute_trade_block` output.
- `TradeBlockedLineupPlayer` if either player id appears in either team's `Lineup` row.

**Soft rejection (does not raise; returns `accepted=false`):**
- `TradeValueTooLow` when offered_value < target_value.

---

## Task 1: Backend — schemas

**Files:**
- Create: `backend/app/schemas/trade.py`

- [ ] **Step 1: Write the schemas**

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict


PlayerType = Literal["skater", "goalie"]


class TradeBlockEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_type: PlayerType
    player_id: int
    team_id: int
    team_name: str
    team_abbreviation: str
    name: str
    age: int
    position: str | None  # None for goalies
    ovr: int
    asking_value: int
    reason: str


class TradeProposalIn(BaseModel):
    target_player_type: PlayerType
    target_player_id: int
    offered_player_type: PlayerType
    offered_player_id: int


class TradeProposalOut(BaseModel):
    accepted: bool
    message: str
    error_code: str | None = None
    acquired_player_id: int | None = None
    acquired_player_type: PlayerType | None = None
    traded_away_player_id: int | None = None
    traded_away_player_type: PlayerType | None = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/trade.py
git commit -m "feat(schemas): trade block + proposal schemas"
```

---

## Task 2: Backend — trade service

**Files:**
- Create: `backend/app/services/trade_service.py`

- [ ] **Step 1: Service skeleton + errors + helpers**

```python
from __future__ import annotations

from typing import Iterable, Literal

from sqlalchemy.orm import Session

from app.errors import (
    DomainError,
    GoalieNotFound,
    NotUserTeam,
    SeasonAlreadyComplete,
    SkaterNotFound,
)
from app.models import Goalie, Lineup, Season, Skater, Team
from app.services.free_agents_service import (
    GOALIE_LINEUP_COLS,
    SKATER_LINEUP_COLS,
    _current_user_team_id,
)
from app.services.generation.players import goalie_overall, skater_overall


PlayerType = Literal["skater", "goalie"]


class TradeOfferInvalid(DomainError):
    code = "TradeOfferInvalid"
    status = 422


class TradeWithOwnTeamNotAllowed(DomainError):
    code = "TradeWithOwnTeamNotAllowed"
    status = 422


class TradeTargetNotAvailable(DomainError):
    code = "TradeTargetNotAvailable"
    status = 404


class TradeBlockedLineupPlayer(DomainError):
    code = "TradeBlockedLineupPlayer"
    status = 422


def _skater_ovr(s: Skater) -> int:
    return skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)


def _goalie_ovr(g: Goalie) -> int:
    return goalie_overall(g.reflexes, g.positioning, g.rebound_control, g.puck_handling, g.mental)


def _is_forward(pos: str) -> bool:
    return pos not in ("LD", "RD")


def _lineup_player_ids(lineup: Lineup | None) -> set[int]:
    if lineup is None:
        return set()
    ids: set[int] = set()
    for col in SKATER_LINEUP_COLS + GOALIE_LINEUP_COLS:
        v = getattr(lineup, col)
        if v is not None:
            ids.add(v)
    return ids


def _require_active_season(db: Session) -> Season:
    season = db.query(Season).order_by(Season.id.desc()).first()
    if season is None:
        raise NotUserTeam()
    if season.status == "complete":
        raise SeasonAlreadyComplete()
    return season
```

- [ ] **Step 2: Trade-block computation**

```python
_BLOCK_MAX_PER_TEAM = 3
_TOP_FWD = 3
_TOP_DEF = 2


def _team_avg_skater_ovr(skaters: list[Skater]) -> float:
    if not skaters:
        return 0.0
    return sum(_skater_ovr(s) for s in skaters) / len(skaters)


def _excluded_top_core(skaters: list[Skater], goalies: list[Goalie]) -> set[tuple[str, int]]:
    fwd = sorted([s for s in skaters if _is_forward(s.position)], key=lambda s: -_skater_ovr(s))
    df = sorted([s for s in skaters if not _is_forward(s.position)], key=lambda s: -_skater_ovr(s))
    g = sorted(goalies, key=lambda x: -_goalie_ovr(x))
    out: set[tuple[str, int]] = set()
    for s in fwd[:_TOP_FWD]:
        out.add(("skater", s.id))
    for s in df[:_TOP_DEF]:
        out.add(("skater", s.id))
    for x in g[:1]:
        out.add(("goalie", x.id))
    return out


def _reason_for_skater(s: Skater, team_avg: float, position_count: int) -> str:
    if s.age >= 32:
        return "Veteran available"
    if (team_avg - _skater_ovr(s)) >= 5:
        return "Depth surplus"
    if position_count >= 4:
        return "Position surplus"
    return "On the block"


def _reason_for_goalie(g: Goalie, team_avg_g: float) -> str:
    if g.age >= 32:
        return "Veteran available"
    if (team_avg_g - _goalie_ovr(g)) >= 4:
        return "Depth surplus"
    return "On the block"


def compute_trade_block(db: Session) -> list[dict]:
    user_team_id = _current_user_team_id(db)
    out: list[dict] = []
    teams = db.query(Team).order_by(Team.id).all()
    for team in teams:
        if team.id == user_team_id:
            continue
        skaters = db.query(Skater).filter(Skater.team_id == team.id).all()
        goalies = db.query(Goalie).filter(Goalie.team_id == team.id).all()
        lineup = db.query(Lineup).filter(Lineup.team_id == team.id).first()
        excluded_ids = _excluded_top_core(skaters, goalies) | {
            ("skater", sid) for sid in _lineup_player_ids(lineup)
        } | {
            ("goalie", gid) for gid in _lineup_player_ids(lineup)
        }
        # Position counts for surplus reason
        pos_counts: dict[str, int] = {}
        for s in skaters:
            pos_counts[s.position] = pos_counts.get(s.position, 0) + 1
        team_avg = _team_avg_skater_ovr(skaters)
        team_avg_g = (sum(_goalie_ovr(g) for g in goalies) / len(goalies)) if goalies else 0.0

        candidates: list[tuple[float, dict]] = []
        for s in skaters:
            if ("skater", s.id) in excluded_ids:
                continue
            score = s.age + (team_avg - _skater_ovr(s))
            ovr = _skater_ovr(s)
            value = ovr + _age_modifier(s.age)  # position_need=0 against own team for asking
            entry = {
                "player_type": "skater",
                "player_id": s.id,
                "team_id": team.id,
                "team_name": team.name,
                "team_abbreviation": team.abbreviation,
                "name": s.name,
                "age": s.age,
                "position": s.position,
                "ovr": ovr,
                "asking_value": value,
                "reason": _reason_for_skater(s, team_avg, pos_counts.get(s.position, 0)),
            }
            candidates.append((score, entry))
        for g in goalies:
            if ("goalie", g.id) in excluded_ids:
                continue
            score = g.age + (team_avg_g - _goalie_ovr(g))
            ovr = _goalie_ovr(g)
            value = ovr + _age_modifier(g.age)
            entry = {
                "player_type": "goalie",
                "player_id": g.id,
                "team_id": team.id,
                "team_name": team.name,
                "team_abbreviation": team.abbreviation,
                "name": g.name,
                "age": g.age,
                "position": None,
                "ovr": ovr,
                "asking_value": value,
                "reason": _reason_for_goalie(g, team_avg_g),
            }
            candidates.append((score, entry))

        candidates.sort(key=lambda kv: -kv[0])
        out.extend(e for _, e in candidates[:_BLOCK_MAX_PER_TEAM])
    return out


def _age_modifier(age: int) -> int:
    if age <= 23:
        return 4
    if age <= 27:
        return 2
    if age <= 31:
        return 0
    if age <= 35:
        return -2
    return -5
```

- [ ] **Step 3: Trade proposal evaluation + swap**

```python
def _position_need_modifier(skater: Skater, receiving_team_id: int, db: Session) -> int:
    same = db.query(Skater).filter(
        Skater.team_id == receiving_team_id, Skater.position == skater.position
    ).count()
    if same <= 1:
        return 3
    if same >= 5:
        return -3
    return 0


def _value_skater(s: Skater, receiving_team_id: int, db: Session) -> int:
    return _skater_ovr(s) + _age_modifier(s.age) + _position_need_modifier(s, receiving_team_id, db)


def _goalie_need_modifier(receiving_team_id: int, db: Session) -> int:
    n = db.query(Goalie).filter(Goalie.team_id == receiving_team_id).count()
    if n <= 1:
        return 3
    if n >= 4:
        return -3
    return 0


def _value_goalie(g: Goalie, receiving_team_id: int, db: Session) -> int:
    return _goalie_ovr(g) + _age_modifier(g.age) + _goalie_need_modifier(receiving_team_id, db)


def propose_trade(
    db: Session,
    target_player_type: PlayerType,
    target_player_id: int,
    offered_player_type: PlayerType,
    offered_player_id: int,
) -> dict:
    season = _require_active_season(db)
    user_team_id = season.user_team_id
    if user_team_id is None:
        raise NotUserTeam()

    if target_player_type != offered_player_type:
        raise TradeOfferInvalid("Same-type trades only.")

    # Load both players
    if target_player_type == "skater":
        target = db.query(Skater).filter(Skater.id == target_player_id).first()
        offered = db.query(Skater).filter(Skater.id == offered_player_id).first()
        if target is None:
            raise SkaterNotFound()
        if offered is None:
            raise SkaterNotFound()
    else:
        target = db.query(Goalie).filter(Goalie.id == target_player_id).first()
        offered = db.query(Goalie).filter(Goalie.id == offered_player_id).first()
        if target is None:
            raise GoalieNotFound()
        if offered is None:
            raise GoalieNotFound()

    # Free agents not tradeable
    if target.team_id is None or offered.team_id is None:
        raise TradeOfferInvalid("Free agents cannot be traded.")
    # Offered must be on user team
    if offered.team_id != user_team_id:
        raise TradeOfferInvalid("Offered player must be on the user team.")
    # Target must be on AI team
    if target.team_id == user_team_id:
        raise TradeWithOwnTeamNotAllowed()

    # Lineup-block check (both teams)
    user_lineup = db.query(Lineup).filter(Lineup.team_id == user_team_id).first()
    target_lineup = db.query(Lineup).filter(Lineup.team_id == target.team_id).first()
    in_lineup = (
        _lineup_player_ids(user_lineup) | _lineup_player_ids(target_lineup)
    )
    if offered.id in in_lineup or target.id in in_lineup:
        raise TradeBlockedLineupPlayer(
            "Players in an active lineup cannot be traded. Update the lineup first."
        )

    # Target must be on the current trade block
    block = compute_trade_block(db)
    if not any(
        e["player_type"] == target_player_type and e["player_id"] == target_player_id
        for e in block
    ):
        raise TradeTargetNotAvailable()

    # Compute values
    if target_player_type == "skater":
        target_value = _value_skater(target, user_team_id, db)
        offered_value = _value_skater(offered, target.team_id, db)
    else:
        target_value = _value_goalie(target, user_team_id, db)
        offered_value = _value_goalie(offered, target.team_id, db)

    if offered_value < target_value:
        return {
            "accepted": False,
            "error_code": "TradeValueTooLow",
            "message": "They want a stronger player in return.",
            "acquired_player_id": None,
            "acquired_player_type": None,
            "traded_away_player_id": None,
            "traded_away_player_type": None,
        }

    # Swap team_ids in one transaction
    other_team_id = target.team_id
    target.team_id, offered.team_id = user_team_id, other_team_id
    db.flush()

    return {
        "accepted": True,
        "error_code": None,
        "message": "Trade accepted.",
        "acquired_player_id": target.id,
        "acquired_player_type": target_player_type,
        "traded_away_player_id": offered.id,
        "traded_away_player_type": offered_player_type,
    }
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/trade_service.py
git commit -m "feat(trades): trade-block computation + proposal evaluation service"
```

---

## Task 3: Backend — API routes

**Files:**
- Create: `backend/app/api/trades.py`
- Modify: `backend/app/api/__init__.py`

- [ ] **Step 1: Write the route module**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.trade import TradeBlockEntryOut, TradeProposalIn, TradeProposalOut
from app.services import trade_service as svc

router = APIRouter(tags=["trades"])


@router.get("/trade-block", response_model=list[TradeBlockEntryOut])
def get_trade_block(db: Session = Depends(get_db)):
    return svc.compute_trade_block(db)


@router.post("/trades/propose", response_model=TradeProposalOut)
def propose_trade(payload: TradeProposalIn, db: Session = Depends(get_db)):
    result = svc.propose_trade(
        db,
        target_player_type=payload.target_player_type,
        target_player_id=payload.target_player_id,
        offered_player_type=payload.offered_player_type,
        offered_player_id=payload.offered_player_id,
    )
    return result
```

- [ ] **Step 2: Register router**

In `backend/app/api/__init__.py` add `trades` to the import block and append `trades.router` to the include tuple.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/trades.py backend/app/api/__init__.py
git commit -m "feat(api): trade-block + propose endpoints"
```

---

## Task 4: Backend — tests

**Files:**
- Create: `backend/tests/test_trade_block.py`
- Create: `backend/tests/test_trade_api.py`

- [ ] **Step 1: Block computation tests**

Cover:
- excludes user-team players entirely
- excludes top-3 forwards / top-2 D / #1 goalie per AI team
- excludes any player whose id is in that team's lineup row
- returns ≤ 3 candidates per AI team
- returns at least 1 candidate per AI team in a normal generated league
- candidate `reason` matches the labelling rules (veteran when age≥32, etc.)
- determinism: two calls with no DB changes produce identical entries (order + content)

- [ ] **Step 2: API + propose tests**

Use existing `db` fixture + `app.dependency_overrides[get_db]` pattern (see `tests/test_sign_release_api.py`).

Cover:
- `GET /api/trade-block` returns expected shape, only AI teams.
- accepted trade swaps team_ids; verify both rows updated; response body shape.
- `TradeWithOwnTeamNotAllowed` when target.team_id == user_team_id.
- `TradeOfferInvalid` cross-type (skater target, goalie offered).
- `TradeOfferInvalid` when offered is a free agent (team_id=null).
- `TradeOfferInvalid` when offered is not on user team.
- `TradeTargetNotAvailable` when target is a top-core player not on the block.
- `TradeBlockedLineupPlayer` when offered or target is in active lineup.
- `SeasonAlreadyComplete` rejects when season status is complete.
- `TradeValueTooLow`: returns `accepted=false` (200), DB unchanged.
- determinism: identical request twice yields identical decisions; first acceptance succeeds, second returns `TradeTargetNotAvailable` (target now on user team).

- [ ] **Step 3: Run tests**

```bash
cd backend && .venv/bin/pytest tests/test_trade_block.py tests/test_trade_api.py -v
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_trade_block.py backend/tests/test_trade_api.py
git commit -m "test(trades): trade-block computation + propose API"
```

---

## Task 5: Frontend — types + queries

**Files:**
- Modify: `frontend/src/api/types.ts`
- Create: `frontend/src/queries/trades.ts`

- [ ] **Step 1: Add types**

```ts
export type PlayerKind = "skater" | "goalie";

export interface TradeBlockEntry {
  player_type: PlayerKind;
  player_id: number;
  team_id: number;
  team_name: string;
  team_abbreviation: string;
  name: string;
  age: number;
  position: string | null;
  ovr: number;
  asking_value: number;
  reason: string;
}

export interface TradeProposalRequest {
  target_player_type: PlayerKind;
  target_player_id: number;
  offered_player_type: PlayerKind;
  offered_player_id: number;
}

export interface TradeProposalResponse {
  accepted: boolean;
  message: string;
  error_code?: string | null;
  acquired_player_id?: number | null;
  acquired_player_type?: PlayerKind | null;
  traded_away_player_id?: number | null;
  traded_away_player_type?: PlayerKind | null;
}
```

- [ ] **Step 2: Write the queries file**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { TradeBlockEntry, TradeProposalRequest, TradeProposalResponse } from "../api/types";

export const useTradeBlock = () =>
  useQuery({
    queryKey: ["trade-block"],
    queryFn: () => api.get<TradeBlockEntry[]>("/api/trade-block"),
  });

export const useProposeTrade = (userTeamId: number | null) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: TradeProposalRequest) =>
      api.post<TradeProposalResponse>("/api/trades/propose", req),
    onSuccess: (_res, req) => {
      qc.invalidateQueries({ queryKey: ["trade-block"] });
      qc.invalidateQueries({ queryKey: ["teams"] });
      if (userTeamId != null) {
        qc.invalidateQueries({ queryKey: ["team", userTeamId] });
        qc.invalidateQueries({ queryKey: ["lineup", userTeamId] });
      }
      // We don't always know target team id from req alone; trade-block refetch covers it.
    },
  });
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/queries/trades.ts
git commit -m "feat(fe): trade types + queries"
```

---

## Task 6: Frontend — Trade Block route

**Files:**
- Create: `frontend/src/routes/trade-block.tsx`
- Modify: `frontend/src/components/Shell.tsx`

- [ ] **Step 1: Page**

Match the layout pattern of `routes/free-agents.tsx`:
- `Shell` with crumbs `["Continental Hockey League", "Trade Block"]`.
- Optional position filter at top (mirrors free-agents filter bar).
- Card with table: Team · Player · Pos · Age · OVR · Reason · Asking · Action.
- "Make Offer" button per row toggles an inline panel beneath the row showing:
  - dropdown of own roster (`useRoster(userTeamId)`) filtered to the matching `player_type` and excluding any player already in the user's lineup;
  - shows offered OVR vs target OVR side-by-side;
  - Submit calls `useProposeTrade`.
- Result message rendered inline (success / rejection) using the response `message`.
- Use existing `attrClass`, `tagClass`-style chip styling for OVR (already in `lib/team-colors.ts`).

- [ ] **Step 2: Add nav entry**

In `Shell.tsx` `NAV` array, add `{ id: "trade-block", label: "Trade Block", to: "/trade-block", icon: <small icon path>, match: (p) => p.startsWith("/trade-block") }` right after `free-agents`.

- [ ] **Step 3: Verify routeTree.gen.ts regenerates**

Run `npm run dev` (or the codegen step the project uses) so TanStack Router picks up the new file. Verify by checking `routeTree.gen.ts` includes `TradeBlockRoute`.

- [ ] **Step 4: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/trade-block.tsx frontend/src/components/Shell.tsx frontend/src/routeTree.gen.ts
git commit -m "feat(fe): trade-block page + nav entry"
```

---

## Task 7: Docs

**Files:**
- Modify: `docs/not-now.md`
- Modify: `docs/product-scope.md`

- [ ] **Step 1: Annotate not-now.md**

Change `- Trades` line under Deferred Gameplay Systems to:

```
- Trades (P1.2 implemented — basic 1-for-1 user-team trade block. Deferred: multi-player, picks, contracts, salary cap, NTC, AI↔AI, history, deadline, negotiation.)
```

- [ ] **Step 2: Add Trades section to product-scope.md**

Under Phase 1 in-scope, after Free Agents (P1.1):

```
### Trades (P1.2)

- Computed trade block per AI team (1–3 candidates each), excluding top core and active-lineup players.
- `/trade-block` page lists candidates with team, name, age, OVR, asking value, reason.
- User team can propose 1-for-1 same-type trades (skater↔skater, goalie↔goalie).
- Backend evaluates deterministically: `value = ovr + age_modifier + position_need_modifier`. Accept iff offered value ≥ target value.
- Accepted trade swaps `team_id` in one transaction.
- Rejections return a clear error code/message.
```

- [ ] **Step 3: Commit**

```bash
git add docs/not-now.md docs/product-scope.md
git commit -m "docs: trades P1.2 in scope; not-now annotated"
```

---

## Task 8: Final verification

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && .venv/bin/pytest
```
Expected: all pass (existing + new).

- [ ] **Step 2: Frontend typecheck**

```bash
cd frontend && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 3: Manual smoke (dev server)**

Start backend + frontend, reset league, navigate to `/trade-block`, verify candidates render, propose a sensible offer (good player for similar one) → expect accept; propose a weak offer → expect rejection message.

- [ ] **Step 4: Open PR**

```bash
git push -u origin feat/trade-block-p1.2
gh pr create --title "feat: Trade Block P1.2" --body-file <prepared>
```

PR description: feature summary, behavior table, links to spec/plan, test summary.

---

## Determinism check

All decisions in this plan are deterministic functions of DB state:
- block computation: pure SQL filter + sort by `(age, team_avg − ovr)`.
- trade evaluation: `ovr + age_mod + position_need_mod`, no RNG.
- swap: single transaction, idempotent (after first swap target is on user team and second proposal hits `TradeWithOwnTeamNotAllowed`).

No `random` import; no time-based logic; no engine seed needed.

## Out of scope (per user spec, restated)

multi-player, picks, salary cap, contracts, retained, NTC, negotiation loop, deadline, AI↔AI trades, history page, role/archetype, chemistry.
