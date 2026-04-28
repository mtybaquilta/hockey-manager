from dataclasses import dataclass
from enum import Enum


class Position(str, Enum):
    LW = "LW"
    C = "C"
    RW = "RW"
    LD = "LD"
    RD = "RD"


class ResultType(str, Enum):
    REG = "REG"
    OT = "OT"
    SO = "SO"


class EventKind(str, Enum):
    SHOT = "shot"
    SAVE = "save"
    GOAL = "goal"
    PENALTY = "penalty"


class Strength(str, Enum):
    EV = "EV"
    PP = "PP"
    SH = "SH"


class ShotQuality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class SimSkater:
    id: int
    position: Position
    skating: int
    shooting: int
    passing: int
    defense: int
    physical: int


@dataclass(frozen=True)
class SimGoalie:
    id: int
    reflexes: int
    positioning: int
    rebound_control: int
    puck_handling: int
    mental: int


@dataclass(frozen=True)
class SimLine:
    skaters: tuple[SimSkater, ...]


@dataclass(frozen=True)
class SimTeamLineup:
    forward_lines: tuple[SimLine, SimLine, SimLine, SimLine]
    defense_pairs: tuple[SimLine, SimLine, SimLine]
    starting_goalie: SimGoalie


@dataclass(frozen=True)
class SimGameInput:
    home: SimTeamLineup
    away: SimTeamLineup
    seed: int


@dataclass(frozen=True)
class SimEvent:
    tick: int
    period: int
    kind: EventKind
    team_is_home: bool
    strength: Strength | None
    primary_skater_id: int | None
    assist1_id: int | None
    assist2_id: int | None
    goalie_id: int | None
    penalty_duration_ticks: int | None = None
    shot_quality: ShotQuality | None = None


@dataclass(frozen=True)
class SimSkaterStat:
    skater_id: int
    goals: int
    assists: int
    shots: int


@dataclass(frozen=True)
class SimGoalieStat:
    goalie_id: int
    shots_against: int
    saves: int
    goals_against: int


@dataclass(frozen=True)
class SimGameResult:
    home_score: int
    away_score: int
    home_shots: int
    away_shots: int
    result_type: ResultType
    events: tuple[SimEvent, ...]
    skater_stats: tuple[SimSkaterStat, ...]
    goalie_stats: tuple[SimGoalieStat, ...]
