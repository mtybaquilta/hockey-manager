from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.advance_service import advance_matchday
from app.services.league_service import get_league


class AdvanceOut(BaseModel):
    advanced_game_ids: list[int]
    current_matchday: int
    season_status: str


class SeasonStatusOut(BaseModel):
    current_matchday: int
    status: str


router = APIRouter(prefix="/season", tags=["season"])


@router.post("/advance", response_model=AdvanceOut)
def post_advance(db: Session = Depends(get_db)):
    res = advance_matchday(db)
    db.commit()
    return AdvanceOut(**res)


@router.get("/status", response_model=SeasonStatusOut)
def get_status(db: Session = Depends(get_db)):
    s = get_league(db)
    return SeasonStatusOut(current_matchday=s.current_matchday, status=s.status)
