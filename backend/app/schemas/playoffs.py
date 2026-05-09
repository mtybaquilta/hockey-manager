from pydantic import BaseModel


class PlayoffGameOut(BaseModel):
    id: int
    matchday: int
    game_in_series: int
    home_team_id: int
    away_team_id: int
    status: str
    home_score: int | None
    away_score: int | None
    result_type: str | None


class PlayoffSeriesOut(BaseModel):
    id: int
    round: int
    bracket_slot: int
    high_seed: int
    low_seed: int
    high_seed_team_id: int | None
    low_seed_team_id: int | None
    wins_high: int
    wins_low: int
    winner_team_id: int | None
    status: str
    games: list[PlayoffGameOut]


class PlayoffRoundOut(BaseModel):
    round: int
    series: list[PlayoffSeriesOut]


class PlayoffsOut(BaseModel):
    phase: str
    season_status: str
    champion_team_id: int | None
    rounds: list[PlayoffRoundOut]
