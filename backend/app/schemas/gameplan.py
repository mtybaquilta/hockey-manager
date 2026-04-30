from typing import Literal

from pydantic import BaseModel

GameplanStyle = Literal["balanced", "offensive", "defensive", "physical"]
GameplanLineUsage = Literal["balanced", "ride_top_lines", "roll_all_lines"]


class GameplanOut(BaseModel):
    team_id: int
    style: GameplanStyle
    line_usage: GameplanLineUsage
    editable: bool


class UpdateGameplanIn(BaseModel):
    style: GameplanStyle
    line_usage: GameplanLineUsage
