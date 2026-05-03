from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import TeamNotFound
from app.models import Goalie, Skater, Team
from app.schemas.team import GoalieOut, RosterOut, SkaterOut, TeamOut

router = APIRouter(prefix="/teams", tags=["teams"])


def _team(db: Session, team_id: int) -> Team:
    t = db.query(Team).filter_by(id=team_id).first()
    if not t:
        raise TeamNotFound(f"team {team_id} not found")
    return t


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
    skaters = db.query(Skater).filter_by(team_id=t.id).order_by(Skater.position, Skater.id).all()
    goalies = db.query(Goalie).filter_by(team_id=t.id).order_by(Goalie.id).all()
    return RosterOut(
        team=TeamOut(id=t.id, name=t.name, abbreviation=t.abbreviation),
        skaters=[
            SkaterOut(
                id=s.id, name=s.name, age=s.age, position=s.position,
                potential=s.potential,
                skating=s.skating, shooting=s.shooting, passing=s.passing,
                defense=s.defense, physical=s.physical,
            )
            for s in skaters
        ],
        goalies=[
            GoalieOut(
                id=g.id, name=g.name, age=g.age,
                potential=g.potential,
                reflexes=g.reflexes, positioning=g.positioning,
                rebound_control=g.rebound_control, puck_handling=g.puck_handling,
                mental=g.mental,
            )
            for g in goalies
        ],
    )
