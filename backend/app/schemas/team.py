from pydantic import BaseModel


class SkaterOut(BaseModel):
    id: int
    name: str
    age: int
    position: str
    skating: int
    shooting: int
    passing: int
    defense: int
    physical: int


class GoalieOut(BaseModel):
    id: int
    name: str
    age: int
    reflexes: int
    positioning: int
    rebound_control: int
    puck_handling: int
    mental: int


class TeamOut(BaseModel):
    id: int
    name: str
    abbreviation: str


class RosterOut(BaseModel):
    team: TeamOut
    skaters: list[SkaterOut]
    goalies: list[GoalieOut]
