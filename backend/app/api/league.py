from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Season, Team
from app.schemas.league import CreateLeagueIn, LeagueOut, SetUserTeamIn, TeamSummary
from app.services import league_service

router = APIRouter(prefix="/league", tags=["league"])


def _serialize(db: Session, season: Season) -> LeagueOut:
    teams = db.query(Team).filter_by(season_id=season.id).order_by(Team.id).all()
    return LeagueOut(
        season_id=season.id,
        seed=season.seed,
        user_team_id=season.user_team_id,
        current_matchday=season.current_matchday,
        status=season.status,
        teams=[TeamSummary(id=t.id, name=t.name, abbreviation=t.abbreviation) for t in teams],
    )


@router.post("", response_model=LeagueOut)
def create(payload: CreateLeagueIn, db: Session = Depends(get_db)):
    season = league_service.create_or_reset_league(db, seed=payload.seed)
    db.commit()
    return _serialize(db, season)


@router.get("", response_model=LeagueOut)
def get(db: Session = Depends(get_db)):
    return _serialize(db, league_service.get_league(db))


@router.put("/user-team", response_model=LeagueOut)
def put_user_team(payload: SetUserTeamIn, db: Session = Depends(get_db)):
    season = league_service.set_user_team(db, payload.team_id)
    db.commit()
    return _serialize(db, season)
