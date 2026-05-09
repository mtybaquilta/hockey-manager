from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from app.errors import (
    DomainError,
    GoalieNotFound,
    NoTradeClause,
    NotUserTeam,
    SeasonAlreadyComplete,
    SkaterNotFound,
)
from app.models import Goalie, Season, Skater, Team
from app.services import contract_service
from app.services.free_agents_service import (
    _clear_goalie_from_lineup,
    _clear_skater_from_lineup,
    _current_user_team_id,
)
from app.services.generation.contracts import market_salary
from app.services.generation.players import goalie_overall, skater_overall
from app.services.player_age import age_from_birth_date

CONTRACT_LENGTH_WEIGHT = 0.5
CONTRACT_SALARY_WEIGHT = 0.001

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


_BLOCK_MAX_PER_TEAM = 3
_TOP_FWD = 3
_TOP_DEF = 2


def _skater_ovr(s: Skater) -> int:
    return skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)


def _goalie_ovr(g: Goalie) -> int:
    return goalie_overall(g.reflexes, g.positioning, g.rebound_control, g.puck_handling, g.mental)


def _is_forward(pos: str) -> bool:
    return pos not in ("LD", "RD")


def _require_active_season(db: Session) -> Season:
    season = db.query(Season).order_by(Season.id.desc()).first()
    if season is None:
        raise NotUserTeam()
    if getattr(season, "status", None) == "complete":
        raise SeasonAlreadyComplete()
    return season


def _contract_dict(c) -> dict | None:
    if c is None:
        return None
    return {
        "id": c.id,
        "length": c.length,
        "signed_season_year": c.signed_season_year,
        "expires_after_year": c.expires_after_year,
        "salary": c.salary,
        "no_trade_clause": c.no_trade_clause,
        "status": c.status,
    }


def _has_ntc(db: Session, player_type: str, player_id: int) -> bool:
    if player_type == "skater":
        c = contract_service.get_active_contract_for_skater(db, player_id)
    else:
        c = contract_service.get_active_contract_for_goalie(db, player_id)
    return bool(c and c.no_trade_clause)


def _contract_modifier(
    db: Session, player_type: str, player_id: int, season_year: int, ovr: int
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


def _team_avg_skater_ovr(skaters: list[Skater]) -> float:
    if not skaters:
        return 0.0
    return sum(_skater_ovr(s) for s in skaters) / len(skaters)


def _excluded_top_core(skaters: list[Skater], goalies: list[Goalie]) -> set[tuple[str, int]]:
    fwd = sorted([s for s in skaters if _is_forward(s.position)], key=lambda s: -_skater_ovr(s))
    df = sorted([s for s in skaters if not _is_forward(s.position)], key=lambda s: -_skater_ovr(s))
    g_sorted = sorted(goalies, key=lambda x: -_goalie_ovr(x))
    out: set[tuple[str, int]] = set()
    for s in fwd[:_TOP_FWD]:
        out.add(("skater", s.id))
    for s in df[:_TOP_DEF]:
        out.add(("skater", s.id))
    for x in g_sorted[:1]:
        out.add(("goalie", x.id))
    return out


def _reason_for_skater(s: Skater, team_avg: float, position_count: int, age: int) -> str:
    if age >= 32:
        return "Veteran available"
    if (team_avg - _skater_ovr(s)) >= 5:
        return "Depth surplus"
    if position_count >= 4:
        return "Position surplus"
    return "On the block"


def _reason_for_goalie(g: Goalie, team_avg_g: float, age: int) -> str:
    if age >= 32:
        return "Veteran available"
    if (team_avg_g - _goalie_ovr(g)) >= 4:
        return "Depth surplus"
    return "On the block"


def compute_trade_block(db: Session) -> list[dict]:
    user_team_id = _current_user_team_id(db)
    season = db.query(Season).order_by(Season.id.desc()).first()
    season_year = season.year if season else 0
    out: list[dict] = []
    teams = db.query(Team).order_by(Team.id).all()
    for team in teams:
        if team.id == user_team_id:
            continue
        skaters = db.query(Skater).filter(Skater.team_id == team.id).all()
        goalies = db.query(Goalie).filter(Goalie.team_id == team.id).all()
        excluded = _excluded_top_core(skaters, goalies)

        pos_counts: dict[str, int] = {}
        for s in skaters:
            pos_counts[s.position] = pos_counts.get(s.position, 0) + 1
        team_avg = _team_avg_skater_ovr(skaters)
        team_avg_g = (sum(_goalie_ovr(g) for g in goalies) / len(goalies)) if goalies else 0.0

        candidates: list[tuple[float, int, dict]] = []
        for s in skaters:
            if ("skater", s.id) in excluded:
                continue
            if _has_ntc(db, "skater", s.id):
                continue
            ovr = _skater_ovr(s)
            age = age_from_birth_date(s.birth_date, season_year)
            score = age + (team_avg - ovr)
            c = contract_service.get_active_contract_for_skater(db, s.id)
            entry = {
                "player_type": "skater",
                "player_id": s.id,
                "team_id": team.id,
                "team_name": team.name,
                "team_abbreviation": team.abbreviation,
                "name": s.name,
                "age": age,
                "position": s.position,
                "ovr": ovr,
                "asking_value": ovr + _age_modifier(age),
                "reason": _reason_for_skater(s, team_avg, pos_counts.get(s.position, 0), age),
                "contract": _contract_dict(c),
            }
            candidates.append((score, s.id, entry))
        for g in goalies:
            if ("goalie", g.id) in excluded:
                continue
            if _has_ntc(db, "goalie", g.id):
                continue
            ovr = _goalie_ovr(g)
            age = age_from_birth_date(g.birth_date, season_year)
            score = age + (team_avg_g - ovr)
            c = contract_service.get_active_contract_for_goalie(db, g.id)
            entry = {
                "player_type": "goalie",
                "player_id": g.id,
                "team_id": team.id,
                "team_name": team.name,
                "team_abbreviation": team.abbreviation,
                "name": g.name,
                "age": age,
                "position": None,
                "ovr": ovr,
                "asking_value": ovr + _age_modifier(age),
                "reason": _reason_for_goalie(g, team_avg_g, age),
                "contract": _contract_dict(c),
            }
            candidates.append((score, g.id, entry))

        candidates.sort(key=lambda kv: (-kv[0], kv[1]))
        out.extend(e for _, _, e in candidates[:_BLOCK_MAX_PER_TEAM])
    return out


def _skater_position_need_modifier(s: Skater, receiving_team_id: int, db: Session) -> int:
    same = db.query(Skater).filter(
        Skater.team_id == receiving_team_id, Skater.position == s.position
    ).count()
    if same <= 1:
        return 3
    if same >= 5:
        return -3
    return 0


def _goalie_need_modifier(receiving_team_id: int, db: Session) -> int:
    n = db.query(Goalie).filter(Goalie.team_id == receiving_team_id).count()
    if n <= 1:
        return 3
    if n >= 4:
        return -3
    return 0


def _value_skater(s: Skater, receiving_team_id: int, db: Session, season_year: int) -> int:
    age = age_from_birth_date(s.birth_date, season_year)
    ovr = _skater_ovr(s)
    contract_mod = _contract_modifier(db, "skater", s.id, season_year, ovr)
    return (
        ovr
        + _age_modifier(age)
        + _skater_position_need_modifier(s, receiving_team_id, db)
        + int(round(contract_mod))
    )


def _value_goalie(g: Goalie, receiving_team_id: int, db: Session, season_year: int) -> int:
    age = age_from_birth_date(g.birth_date, season_year)
    ovr = _goalie_ovr(g)
    contract_mod = _contract_modifier(db, "goalie", g.id, season_year, ovr)
    return (
        ovr
        + _age_modifier(age)
        + _goalie_need_modifier(receiving_team_id, db)
        + int(round(contract_mod))
    )


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

    if target_player_type == "skater":
        target_s = db.query(Skater).filter(Skater.id == target_player_id).first()
        offered_s = db.query(Skater).filter(Skater.id == offered_player_id).first()
        if target_s is None or offered_s is None:
            raise SkaterNotFound()
        target_team_id = target_s.team_id
        offered_team_id = offered_s.team_id
        target_id = target_s.id
        offered_id = offered_s.id
    else:
        target_g = db.query(Goalie).filter(Goalie.id == target_player_id).first()
        offered_g = db.query(Goalie).filter(Goalie.id == offered_player_id).first()
        if target_g is None or offered_g is None:
            raise GoalieNotFound()
        target_team_id = target_g.team_id
        offered_team_id = offered_g.team_id
        target_id = target_g.id
        offered_id = offered_g.id

    if target_team_id is None or offered_team_id is None:
        raise TradeOfferInvalid("Free agents cannot be traded.")
    if offered_team_id != user_team_id:
        raise TradeOfferInvalid("Offered player must be on the user team.")
    if target_team_id == user_team_id:
        raise TradeWithOwnTeamNotAllowed()

    if _has_ntc(db, target_player_type, target_id) or _has_ntc(db, offered_player_type, offered_id):
        raise NoTradeClause("trade rejected: no-trade clause")

    block = compute_trade_block(db)
    if not any(
        e["player_type"] == target_player_type and e["player_id"] == target_player_id
        for e in block
    ):
        raise TradeTargetNotAvailable()

    season_year = season.year
    if target_player_type == "skater":
        target_value = _value_skater(target_s, user_team_id, db, season_year)
        offered_value = _value_skater(offered_s, target_team_id, db, season_year)
    else:
        target_value = _value_goalie(target_g, user_team_id, db, season_year)
        offered_value = _value_goalie(offered_g, target_team_id, db, season_year)

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

    if target_player_type == "skater":
        # Clear lineup slots on both teams before reassigning team_id (matches release flow).
        _clear_skater_from_lineup(db, target_team_id, target_s.id)
        _clear_skater_from_lineup(db, user_team_id, offered_s.id)
        target_s.team_id = user_team_id
        offered_s.team_id = target_team_id
    else:
        _clear_goalie_from_lineup(db, target_team_id, target_g.id)
        _clear_goalie_from_lineup(db, user_team_id, offered_g.id)
        target_g.team_id = user_team_id
        offered_g.team_id = target_team_id
    db.flush()

    return {
        "accepted": True,
        "error_code": None,
        "message": "Trade accepted.",
        "acquired_player_id": target_id,
        "acquired_player_type": target_player_type,
        "traded_away_player_id": offered_id,
        "traded_away_player_type": offered_player_type,
    }
