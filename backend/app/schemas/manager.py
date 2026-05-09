from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ManagerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    current_team_id: int | None
    created_at: datetime
    seasons_completed: int
    championships_won: int
    career_wins: int
    career_losses: int
    career_ot_losses: int


class CreateManagerIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class SetTeamIn(BaseModel):
    team_id: int
