from pydantic import BaseModel


class SkaterSeasonStatsOut(BaseModel):
    season_id: int
    gp: int
    g: int
    a: int
    pts: int
    sog: int


class SkaterCareerOut(BaseModel):
    player_id: int
    name: str
    by_season: list[SkaterSeasonStatsOut]
    totals: SkaterSeasonStatsOut


class GoalieSeasonStatsOut(BaseModel):
    season_id: int
    gp: int
    shots_against: int
    saves: int
    goals_against: int
    sv_pct: float


class GoalieCareerOut(BaseModel):
    player_id: int
    name: str
    by_season: list[GoalieSeasonStatsOut]
    totals: GoalieSeasonStatsOut
