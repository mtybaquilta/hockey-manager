from pydantic import BaseModel, ConfigDict, computed_field

from app.services.generation.players import goalie_overall, skater_overall
from app.services.player_age import age_from_birth_date


class FreeAgentSkaterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    position: str
    potential: int
    development_type: str
    skating: int
    shooting: int
    passing: int
    defense: int
    physical: int

    @computed_field  # type: ignore[misc]
    @property
    def ovr(self) -> int:
        return skater_overall(
            self.skating, self.shooting, self.passing, self.defense, self.physical
        )


class FreeAgentGoalieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    potential: int
    development_type: str
    reflexes: int
    positioning: int
    rebound_control: int
    puck_handling: int
    mental: int

    @computed_field  # type: ignore[misc]
    @property
    def ovr(self) -> int:
        return goalie_overall(
            self.reflexes,
            self.positioning,
            self.rebound_control,
            self.puck_handling,
            self.mental,
        )


class SignReleaseSkaterOut(FreeAgentSkaterOut):
    team_id: int | None = None


class SignReleaseGoalieOut(FreeAgentGoalieOut):
    team_id: int | None = None


def skater_to_out(s, season_year: int) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "age": age_from_birth_date(s.birth_date, season_year),
        "position": s.position,
        "potential": s.potential,
        "development_type": s.development_type,
        "skating": s.skating,
        "shooting": s.shooting,
        "passing": s.passing,
        "defense": s.defense,
        "physical": s.physical,
    }


def goalie_to_out(g, season_year: int) -> dict:
    return {
        "id": g.id,
        "name": g.name,
        "age": age_from_birth_date(g.birth_date, season_year),
        "potential": g.potential,
        "development_type": g.development_type,
        "reflexes": g.reflexes,
        "positioning": g.positioning,
        "rebound_control": g.rebound_control,
        "puck_handling": g.puck_handling,
        "mental": g.mental,
    }
