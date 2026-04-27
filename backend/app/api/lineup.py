from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import TeamNotFound
from app.models import Lineup, Team
from app.schemas.lineup import LineupOut, UpdateLineupIn
from app.services import lineup_service

router = APIRouter(prefix="/teams", tags=["lineup"])


def _serialize(lu: Lineup) -> LineupOut:
    return LineupOut(**{c.name: getattr(lu, c.name) for c in lu.__table__.columns if c.name != "id"})


@router.get("/{team_id}/lineup", response_model=LineupOut)
def get_lineup(team_id: int, db: Session = Depends(get_db)):
    if not db.query(Team).filter_by(id=team_id).first():
        raise TeamNotFound(f"team {team_id} not found")
    lu = db.query(Lineup).filter_by(team_id=team_id).first()
    if not lu:
        raise TeamNotFound(f"lineup for team {team_id} not found")
    return _serialize(lu)


@router.put("/{team_id}/lineup", response_model=LineupOut)
def update_lineup_endpoint(team_id: int, payload: UpdateLineupIn, db: Session = Depends(get_db)):
    lu = lineup_service.update_lineup(db, team_id, payload)
    db.commit()
    return _serialize(lu)
