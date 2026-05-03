from typing import Literal

from pydantic import BaseModel, ConfigDict


PlayerType = Literal["skater", "goalie"]


class TradeBlockEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_type: PlayerType
    player_id: int
    team_id: int
    team_name: str
    team_abbreviation: str
    name: str
    age: int
    position: str | None
    ovr: int
    asking_value: int
    reason: str


class TradeProposalIn(BaseModel):
    target_player_type: PlayerType
    target_player_id: int
    offered_player_type: PlayerType
    offered_player_id: int


class TradeProposalOut(BaseModel):
    accepted: bool
    message: str
    error_code: str | None = None
    acquired_player_id: int | None = None
    acquired_player_type: PlayerType | None = None
    traded_away_player_id: int | None = None
    traded_away_player_type: PlayerType | None = None
