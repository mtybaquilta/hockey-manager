from pydantic import BaseModel


class DevelopmentEventOut(BaseModel):
    attribute: str
    old_value: int
    new_value: int
    delta: int
    reason: str


class SeasonProgressionOut(BaseModel):
    player_type: str
    player_id: int
    player_name: str
    team_id: int | None
    age_before: int
    age_after: int
    overall_before: int
    overall_after: int
    potential: int
    development_type: str
    summary_reason: str
    events: list[DevelopmentEventOut]


class DevelopmentSummaryOut(BaseModel):
    season_id: int
    progressions: list[SeasonProgressionOut]


class StartNextSeasonOut(BaseModel):
    new_season_id: int
    development_summary: DevelopmentSummaryOut
