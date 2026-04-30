from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Game
from app.schemas.schedule import GameSummary, ScheduleOut
from app.services.league_service import get_league

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("", response_model=ScheduleOut)
def list_schedule(db: Session = Depends(get_db)):
    season = get_league(db)
    games = (
        db.query(Game)
        .filter_by(season_id=season.id)
        .order_by(Game.matchday, Game.id)
        .all()
    )
    return ScheduleOut(
        games=[
            GameSummary(
                id=g.id,
                matchday=g.matchday,
                home_team_id=g.home_team_id,
                away_team_id=g.away_team_id,
                status=g.status,
                home_score=g.home_score,
                away_score=g.away_score,
                result_type=g.result_type,
            )
            for g in games
        ]
    )
