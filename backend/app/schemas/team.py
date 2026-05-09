from pydantic import BaseModel

from app.schemas.contract import ContractOut


class SkaterOut(BaseModel):
    id: int
    name: str
    age: int
    position: str
    potential: int
    skating: int
    shooting: int
    passing: int
    defense: int
    physical: int
    contract: ContractOut | None = None


class GoalieOut(BaseModel):
    id: int
    name: str
    age: int
    potential: int
    reflexes: int
    positioning: int
    rebound_control: int
    puck_handling: int
    mental: int
    contract: ContractOut | None = None


class TeamOut(BaseModel):
    id: int
    name: str
    abbreviation: str


class RosterOut(BaseModel):
    team: TeamOut
    skaters: list[SkaterOut]
    goalies: list[GoalieOut]
