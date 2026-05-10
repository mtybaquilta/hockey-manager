"""Pure trade-evaluation primitives (no FastAPI; uses SQLAlchemy session for lookups)."""
from __future__ import annotations

from dataclasses import dataclass  # noqa: F401
from typing import Literal

from sqlalchemy.orm import Session

from app.models import Goalie, Skater, Team  # noqa: F401


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
