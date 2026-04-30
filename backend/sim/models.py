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
class SimGameplan:
    style: str  # "balanced" | "offensive" | "defensive" | "physical"
    line_usage: str  # "balanced" | "ride_top_lines" | "roll_all_lines"


@dataclass(frozen=True)
class SimTeamInput:
    lineup: SimTeamLineup
    gameplan: SimGameplan


@dataclass(frozen=True)
class SimGameInput:
    home: SimTeamInput
    away: SimTeamInput
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
    # 4 entries: P1, P2, P3, OT. Shootout deciding goal is not counted here.
    home_goals_by_period: tuple[int, int, int, int]
    away_goals_by_period: tuple[int, int, int, int]
    home_shots_by_period: tuple[int, int, int, int]
    away_shots_by_period: tuple[int, int, int, int]
