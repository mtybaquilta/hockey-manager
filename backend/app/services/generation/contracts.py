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
