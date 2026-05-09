from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Season
from app.schemas.contract import ContractOut, SignContractIn
from app.schemas.free_agents import (
    FreeAgentGoalieOut,
    FreeAgentSkaterOut,
    SignReleaseGoalieOut,
    SignReleaseSkaterOut,
    goalie_to_out,
    skater_to_out,
)
from app.services import contract_service
from app.services import free_agents_service as svc

router = APIRouter(tags=["free-agents"])


def _current_season_year(db: Session) -> int:
    season = db.query(Season).order_by(Season.id.desc()).first()
    return season.year if season else 0


class SignSkaterOut(SignReleaseSkaterOut):
    contract: ContractOut


class SignGoalieOut(SignReleaseGoalieOut):
    contract: ContractOut


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
    rows = svc.list_free_agent_skaters(
        db,
        position=position,
        min_ovr=min_ovr,
        min_potential=min_potential,
        max_age=max_age,
        sort=sort,  # type: ignore[arg-type]
        order=order,  # type: ignore[arg-type]
    )
    year = _current_season_year(db)
    return [FreeAgentSkaterOut.model_validate(skater_to_out(s, year)) for s in rows]


@router.get("/free-agents/goalies", response_model=list[FreeAgentGoalieOut])
def list_goalies(
    min_ovr: int | None = Query(default=None),
    min_potential: int | None = Query(default=None),
    max_age: int | None = Query(default=None),
    sort: str = Query(default="ovr"),
    order: str = Query(default="desc"),
    db: Session = Depends(get_db),
):
    rows = svc.list_free_agent_goalies(
        db,
        min_ovr=min_ovr,
        min_potential=min_potential,
        max_age=max_age,
        sort=sort,  # type: ignore[arg-type]
        order=order,  # type: ignore[arg-type]
    )
    year = _current_season_year(db)
    return [FreeAgentGoalieOut.model_validate(goalie_to_out(g, year)) for g in rows]


@router.post(
    "/teams/{team_id}/sign/skater/{skater_id}", response_model=SignSkaterOut
)
def sign_skater(
    team_id: int, skater_id: int, body: SignContractIn, db: Session = Depends(get_db)
):
    sk = svc.sign_skater(
        db, team_id, skater_id,
        length=body.length, salary=body.salary, no_trade_clause=body.no_trade_clause,
    )
    contract = contract_service.get_active_contract_for_skater(db, skater_id)
    year = _current_season_year(db)
    db.commit()
    return SignSkaterOut.model_validate(
        {**skater_to_out(sk, year), "team_id": sk.team_id, "contract": contract}
    )


@router.post(
    "/teams/{team_id}/sign/goalie/{goalie_id}", response_model=SignGoalieOut
)
def sign_goalie(
    team_id: int, goalie_id: int, body: SignContractIn, db: Session = Depends(get_db)
):
    g = svc.sign_goalie(
        db, team_id, goalie_id,
        length=body.length, salary=body.salary, no_trade_clause=body.no_trade_clause,
    )
    contract = contract_service.get_active_contract_for_goalie(db, goalie_id)
    year = _current_season_year(db)
    db.commit()
    return SignGoalieOut.model_validate(
        {**goalie_to_out(g, year), "team_id": g.team_id, "contract": contract}
    )


@router.post(
    "/teams/{team_id}/release/skater/{skater_id}", response_model=SignReleaseSkaterOut
)
def release_skater(team_id: int, skater_id: int, db: Session = Depends(get_db)):
    sk = svc.release_skater(db, team_id, skater_id)
    year = _current_season_year(db)
    db.commit()
    return SignReleaseSkaterOut.model_validate(
        {**skater_to_out(sk, year), "team_id": sk.team_id}
    )


@router.post(
    "/teams/{team_id}/release/goalie/{goalie_id}", response_model=SignReleaseGoalieOut
)
def release_goalie(team_id: int, goalie_id: int, db: Session = Depends(get_db)):
    g = svc.release_goalie(db, team_id, goalie_id)
    year = _current_season_year(db)
    db.commit()
    return SignReleaseGoalieOut.model_validate(
        {**goalie_to_out(g, year), "team_id": g.team_id}
    )
