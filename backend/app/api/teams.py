from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import TeamNotFound
from app.models import Goalie, Season, Skater, Team
from app.schemas.contract import ContractOut
from app.schemas.team import GoalieOut, RosterOut, SkaterOut, TeamOut
from app.services import contract_service
from app.services.player_age import age_from_birth_date

router = APIRouter(prefix="/teams", tags=["teams"])


def _team(db: Session, team_id: int) -> Team:
    t = db.query(Team).filter_by(id=team_id).first()
    if not t:
        raise TeamNotFound(f"team {team_id} not found")
    return t


def _current_season_year(db: Session) -> int:
    season = db.query(Season).order_by(Season.id.desc()).first()
    return season.year if season else 0


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return [
        TeamOut(id=t.id, name=t.name, abbreviation=t.abbreviation)
        for t in db.query(Team).order_by(Team.id).all()
    ]


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: int, db: Session = Depends(get_db)):
    t = _team(db, team_id)
    return TeamOut(id=t.id, name=t.name, abbreviation=t.abbreviation)


@router.get("/{team_id}/roster", response_model=RosterOut)
def get_roster(team_id: int, db: Session = Depends(get_db)):
    t = _team(db, team_id)
    year = _current_season_year(db)
    skaters = db.query(Skater).filter_by(team_id=t.id).order_by(Skater.position, Skater.id).all()
    goalies = db.query(Goalie).filter_by(team_id=t.id).order_by(Goalie.id).all()

    skater_out = []
    for s in skaters:
        c = contract_service.get_active_contract_for_skater(db, s.id)
        skater_out.append(
            SkaterOut(
                id=s.id, name=s.name, age=age_from_birth_date(s.birth_date, year),
                position=s.position, potential=s.potential,
                skating=s.skating, shooting=s.shooting, passing=s.passing,
                defense=s.defense, physical=s.physical,
                contract=ContractOut.model_validate(c) if c else None,
            )
        )
    goalie_out = []
    for g in goalies:
        c = contract_service.get_active_contract_for_goalie(db, g.id)
        goalie_out.append(
            GoalieOut(
                id=g.id, name=g.name, age=age_from_birth_date(g.birth_date, year),
                potential=g.potential,
                reflexes=g.reflexes, positioning=g.positioning,
                rebound_control=g.rebound_control, puck_handling=g.puck_handling,
                mental=g.mental,
                contract=ContractOut.model_validate(c) if c else None,
            )
        )
    return RosterOut(
        team=TeamOut(id=t.id, name=t.name, abbreviation=t.abbreviation),
        skaters=skater_out,
        goalies=goalie_out,
    )
