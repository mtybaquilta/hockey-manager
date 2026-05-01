from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.gameplan import GameplanOut, GameplansListOut, UpdateGameplanIn
from app.services import gameplan_service

router = APIRouter(prefix="/teams", tags=["gameplan"])
list_router = APIRouter(prefix="/gameplans", tags=["gameplan"])


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


@list_router.get("", response_model=GameplansListOut)
def list_all_gameplans(db: Session = Depends(get_db)):
    rows = gameplan_service.list_gameplans(db)
    return GameplansListOut(
        rows=[
            GameplanOut(
                team_id=gp.team_id,
                style=gp.style,
                line_usage=gp.line_usage,
                editable=gameplan_service.is_editable(db, gp.team_id),
            )
            for gp in rows
        ]
    )
