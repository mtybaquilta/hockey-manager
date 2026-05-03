from pydantic import BaseModel, ConfigDict, computed_field

from app.services.generation.players import goalie_overall, skater_overall


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
