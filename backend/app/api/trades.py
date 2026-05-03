from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.trade import TradeBlockEntryOut, TradeProposalIn, TradeProposalOut
from app.services import trade_service as svc

router = APIRouter(tags=["trades"])


@router.get("/trade-block", response_model=list[TradeBlockEntryOut])
def get_trade_block(db: Session = Depends(get_db)):
    return svc.compute_trade_block(db)


@router.post("/trades/propose", response_model=TradeProposalOut)
def propose_trade(payload: TradeProposalIn, db: Session = Depends(get_db)):
    return svc.propose_trade(
        db,
        target_player_type=payload.target_player_type,
        target_player_id=payload.target_player_id,
        offered_player_type=payload.offered_player_type,
        offered_player_id=payload.offered_player_id,
    )
