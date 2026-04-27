from pydantic import BaseModel


class EventOut(BaseModel):
    tick: int
    kind: str
    team_id: int
    primary_skater_id: int | None
    assist1_id: int | None
    assist2_id: int | None
    goalie_id: int | None


class SkaterStatOut(BaseModel):
    skater_id: int
    goals: int
    assists: int
    shots: int


class GoalieStatOut(BaseModel):
    goalie_id: int
    shots_against: int
    saves: int
    goals_against: int


class GameDetailOut(BaseModel):
    id: int
    matchday: int
    home_team_id: int
    away_team_id: int
    status: str
    home_score: int | None
    away_score: int | None
    home_shots: int | None
    away_shots: int | None
    result_type: str | None
    events: list[EventOut]
    skater_stats: list[SkaterStatOut]
    goalie_stats: list[GoalieStatOut]
