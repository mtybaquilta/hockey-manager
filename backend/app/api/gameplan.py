from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.gameplan import GameplanOut, UpdateGameplanIn
from app.services import gameplan_service

router = APIRouter(prefix="/teams", tags=["gameplan"])


def _to_out(gp, editable: bool) -> GameplanOut:
    return GameplanOut(
        team_id=gp.team_id,
        style=gp.style,
        line_usage=gp.line_usage,
        editable=editable,
    )


@router.get("/{team_id}/gameplan", response_model=GameplanOut)
def get_gameplan(team_id: int, db: Session = Depends(get_db)):
    gp = gameplan_service.get_team_gameplan(db, team_id)
    return _to_out(gp, gameplan_service.is_editable(db, team_id))


@router.put("/{team_id}/gameplan", response_model=GameplanOut)
def put_gameplan(team_id: int, payload: UpdateGameplanIn, db: Session = Depends(get_db)):
    gp = gameplan_service.update_user_team_gameplan(
        db, team_id, payload.style, payload.line_usage
    )
    db.commit()
    return _to_out(gp, editable=True)
