"""Pure trade-evaluation primitives (no FastAPI; uses SQLAlchemy session for lookups)."""
from __future__ import annotations

from dataclasses import dataclass  # noqa: F401
from typing import Literal

from sqlalchemy.orm import Session

from app.models import Goalie, Skater, Team  # noqa: F401 (Goalie unused until later tasks)


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
