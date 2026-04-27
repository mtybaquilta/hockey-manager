from pydantic import BaseModel


class CreateLeagueIn(BaseModel):
    seed: int | None = None


class TeamSummary(BaseModel):
    id: int
    name: str
    abbreviation: str


class LeagueOut(BaseModel):
    season_id: int
    seed: int
    user_team_id: int | None
    current_matchday: int
    status: str
    teams: list[TeamSummary]


class SetUserTeamIn(BaseModel):
    team_id: int
