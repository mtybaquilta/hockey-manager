from pydantic import BaseModel


class GameSummary(BaseModel):
    id: int
    matchday: int
    home_team_id: int
    away_team_id: int
    status: str
    home_score: int | None
    away_score: int | None
    result_type: str | None


class ScheduleOut(BaseModel):
    games: list[GameSummary]
