"""Pure trade-evaluation primitives (no FastAPI; uses SQLAlchemy session for lookups)."""
from __future__ import annotations

from dataclasses import dataclass  # noqa: F401
from typing import Literal

from sqlalchemy.orm import Session  # noqa: F401

from app.models import Goalie, Skater, Team  # noqa: F401


PlayerType = Literal["skater", "goalie"]


def age_modifier(age: int) -> int:
    if age <= 23:
        return 4
    if age <= 27:
        return 2
    if age <= 31:
        return 0
    if age <= 35:
        return -2
    return -5


def potential_modifier(potential: int, age: int) -> int:
    if age <= 23 and potential >= 90:
        return 6
    if age <= 23 and potential >= 85:
        return 4
    if age <= 25 and potential >= 85:
        return 2
    if age >= 30 and potential < 80:
        return -1
    return 0
