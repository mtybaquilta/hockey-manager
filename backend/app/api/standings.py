from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Standing
from app.schemas.standings import StandingOut, StandingsOut
from app.services.league_service import get_league

router = APIRouter(prefix="/standings", tags=["standings"])


@router.get("", response_model=StandingsOut)
def get_standings(db: Session = Depends(get_db)):
    season = get_league(db)
    rows = db.query(Standing).filter_by(season_id=season.id).all()
    rows.sort(key=lambda s: (-s.points, -(s.goals_for - s.goals_against), s.team_id))
    return StandingsOut(
        rows=[
            StandingOut(
                team_id=r.team_id,
                games_played=r.games_played,
                wins=r.wins,
                losses=r.losses,
                ot_losses=r.ot_losses,
                points=r.points,
                goals_for=r.goals_for,
                goals_against=r.goals_against,
            )
            for r in rows
        ]
    )
