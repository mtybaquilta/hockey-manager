from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.free_agents import (
    FreeAgentGoalieOut,
    FreeAgentSkaterOut,
    SignReleaseGoalieOut,
    SignReleaseSkaterOut,
)
from app.services import free_agents_service as svc

router = APIRouter(tags=["free-agents"])


@router.get("/free-agents/skaters", response_model=list[FreeAgentSkaterOut])
def list_skaters(
    position: str | None = Query(default=None),
    min_ovr: int | None = Query(default=None),
    min_potential: int | None = Query(default=None),
    max_age: int | None = Query(default=None),
    sort: str = Query(default="ovr"),
    order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    return svc.list_free_agent_skaters(
        db,
        position=position,
        min_ovr=min_ovr,
        min_potential=min_potential,
        max_age=max_age,
        sort=sort,  # type: ignore[arg-type]
        order=order,  # type: ignore[arg-type]
    )


@router.get("/free-agents/goalies", response_model=list[FreeAgentGoalieOut])
def list_goalies(
    min_ovr: int | None = Query(default=None),
    min_potential: int | None = Query(default=None),
    max_age: int | None = Query(default=None),
    sort: str = Query(default="ovr"),
    order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    return svc.list_free_agent_goalies(
        db,
        min_ovr=min_ovr,
        min_potential=min_potential,
        max_age=max_age,
        sort=sort,  # type: ignore[arg-type]
        order=order,  # type: ignore[arg-type]
    )


@router.post(
    "/teams/{team_id}/sign/skater/{skater_id}", response_model=SignReleaseSkaterOut
)
def sign_skater(team_id: int, skater_id: int, db: Session = Depends(get_db)):
    sk = svc.sign_skater(db, team_id, skater_id)
    db.commit()
    return sk


@router.post(
    "/teams/{team_id}/sign/goalie/{goalie_id}", response_model=SignReleaseGoalieOut
)
def sign_goalie(team_id: int, goalie_id: int, db: Session = Depends(get_db)):
    g = svc.sign_goalie(db, team_id, goalie_id)
    db.commit()
    return g


@router.post(
    "/teams/{team_id}/release/skater/{skater_id}", response_model=SignReleaseSkaterOut
)
def release_skater(team_id: int, skater_id: int, db: Session = Depends(get_db)):
    sk = svc.release_skater(db, team_id, skater_id)
    db.commit()
    return sk


@router.post(
    "/teams/{team_id}/release/goalie/{goalie_id}", response_model=SignReleaseGoalieOut
)
def release_goalie(team_id: int, goalie_id: int, db: Session = Depends(get_db)):
    g = svc.release_goalie(db, team_id, goalie_id)
    db.commit()
    return g
