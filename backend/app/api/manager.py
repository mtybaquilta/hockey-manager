from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.manager import CreateManagerIn, ManagerProfileOut, SetTeamIn
from app.services import manager_profile_service as svc

router = APIRouter(prefix="/manager-profile", tags=["manager"])


@router.get("", response_model=ManagerProfileOut | None)
def get_profile(db: Session = Depends(get_db)):
    p = svc.get_active_profile(db)
    return p


@router.post("", response_model=ManagerProfileOut)
def create_profile(payload: CreateManagerIn, db: Session = Depends(get_db)):
    p = svc.create_profile(db, name=payload.name)
    db.commit()
    return p


@router.put("/team", response_model=ManagerProfileOut)
def set_team(payload: SetTeamIn, db: Session = Depends(get_db)):
    p = svc.require_active_profile(db)
    p = svc.set_team(db, p.id, payload.team_id)
    db.commit()
    return p
