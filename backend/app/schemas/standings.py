from pydantic import BaseModel


class StandingOut(BaseModel):
    team_id: int
    games_played: int
    wins: int
    losses: int
    ot_losses: int
    points: int
    goals_for: int
    goals_against: int


class StandingsOut(BaseModel):
    rows: list[StandingOut]
