from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PlayerType = Literal["skater", "goalie"]
Outlook = Literal["accept", "close", "reject"]


class OfferSidePlayer(BaseModel):
    player_type: PlayerType
    player_id: int


class RejectionReason(BaseModel):
    code: Literal[
        "ValueTooLow",
        "NoTradeClause",
        "PositionNeedMismatch",
        "TopProspect",
        "RosterFloor",
    ]
    message: str
    player_type: PlayerType | None = None
    player_id: int | None = None


class TradeWarning(BaseModel):
    code: Literal["RosterBelowActiveFloor", "LineupSlotsCleared"]
    message: str
    team_id: int | None = None


class EvaluateRequest(BaseModel):
    partner_team_id: int
    offered: list[OfferSidePlayer] = Field(min_length=1, max_length=3)
    requested: list[OfferSidePlayer] = Field(min_length=1, max_length=3)


class EvaluateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    accepted: bool
    outlook: Outlook
    offered_value: int
    requested_value: int
    rejection_reasons: list[RejectionReason]
    warnings: list[TradeWarning]


class AcquiredPlayer(BaseModel):
    player_type: PlayerType
    player_id: int


class ExecuteResponse(EvaluateResponse):
    acquired: list[AcquiredPlayer]
    traded_away: list[AcquiredPlayer]
