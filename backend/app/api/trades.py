from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.trade import (
    AcquiredPlayer,
    EvaluateRequest,
    EvaluateResponse,
    ExecuteResponse,
    RejectionReason,
    TradeWarning,
)
from app.services import trade_service as svc
from app.services.trade_eval import OfferPlayer

router = APIRouter(tags=["trades"])


def _to_offer(items) -> list[OfferPlayer]:
    return [OfferPlayer(player_type=i.player_type, player_id=i.player_id) for i in items]


def _outcome_to_response(o) -> dict:
    return {
        "accepted": o.accepted,
        "outlook": o.outlook,
        "offered_value": o.offered_value,
        "requested_value": o.requested_value,
        "rejection_reasons": [
            RejectionReason(code=r.code, message=r.message, player_type=r.player_type, player_id=r.player_id)
            for r in o.rejection_reasons
        ],
        "warnings": [
            TradeWarning(code=w.code, message=w.message, team_id=w.team_id)
            for w in o.warnings
        ],
    }


@router.post("/trades/evaluate", response_model=EvaluateResponse)
def evaluate_trade(payload: EvaluateRequest, db: Session = Depends(get_db)):
    outcome = svc.evaluate_offer(
        db,
        partner_team_id=payload.partner_team_id,
        offered=_to_offer(payload.offered),
        requested=_to_offer(payload.requested),
    )
    return _outcome_to_response(outcome)


@router.post("/trades/execute", response_model=ExecuteResponse)
def execute_trade(payload: EvaluateRequest, db: Session = Depends(get_db)):
    outcome, acquired, traded_away = svc.execute_offer(
        db,
        partner_team_id=payload.partner_team_id,
        offered=_to_offer(payload.offered),
        requested=_to_offer(payload.requested),
    )
    body = _outcome_to_response(outcome)
    body["acquired"] = [AcquiredPlayer(player_type=p.player_type, player_id=p.player_id) for p in acquired]
    body["traded_away"] = [AcquiredPlayer(player_type=p.player_type, player_id=p.player_id) for p in traded_away]
    return body
