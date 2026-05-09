from datetime import date
from typing import Literal

from sqlalchemy.orm import Session

from app.errors import (
    ContractTermsInvalid,
    DomainError,
    GoalieNotFound,
    NoActiveSeason,
    NotUserTeam,
    SkaterNotFound,
    TeamNotFound,
)
from app.models import Goalie, Lineup, Season, Skater, Team
from app.services import contract_service
from app.services.generation.contracts import SALARY_MAX, SALARY_MIN

SkaterSort = Literal["ovr", "potential", "age", "position"]
GoalieSort = Literal["ovr", "potential", "age"]
Order = Literal["asc", "desc"]

SKATER_LINEUP_COLS = (
    "line1_lw_id", "line1_c_id", "line1_rw_id",
    "line2_lw_id", "line2_c_id", "line2_rw_id",
    "line3_lw_id", "line3_c_id", "line3_rw_id",
    "line4_lw_id", "line4_c_id", "line4_rw_id",
    "pair1_ld_id", "pair1_rd_id",
    "pair2_ld_id", "pair2_rd_id",
    "pair3_ld_id", "pair3_rd_id",
)
GOALIE_LINEUP_COLS = ("starting_goalie_id", "backup_goalie_id")


class PlayerNotFreeAgent(DomainError):
    code = "PlayerNotFreeAgent"
    status = 400


class PlayerNotOnTeam(DomainError):
    code = "PlayerNotOnTeam"
    status = 400


def _current_user_team_id(db: Session) -> int | None:
    season = db.query(Season).order_by(Season.id.desc()).first()
    return season.user_team_id if season else None


def _current_season_year(db: Session) -> int:
    season = db.query(Season).order_by(Season.id.desc()).first()
    if not season:
        raise NoActiveSeason("no active season")
    return season.year


def _max_birth_date_for_max_age(season_year: int, max_age: int) -> date:
    return date(season_year - max_age, 1, 1)


def _validate_terms(length: int, salary: int) -> None:
    if not (1 <= length <= 8):
        raise ContractTermsInvalid(f"length {length} not in [1, 8]")
    if not (SALARY_MIN <= salary <= SALARY_MAX):
        raise ContractTermsInvalid(f"salary {salary} not in [{SALARY_MIN}, {SALARY_MAX}]")


def _skater_ovr_expr():
    return (
        Skater.skating + Skater.shooting + Skater.passing + Skater.defense + Skater.physical
    ) / 5.0


def _goalie_ovr_expr():
    return (
        Goalie.reflexes + Goalie.positioning + Goalie.rebound_control
        + Goalie.puck_handling + Goalie.mental
    ) / 5.0


def list_free_agent_skaters(
    db: Session,
    *,
    position: str | None = None,
    min_ovr: int | None = None,
    min_potential: int | None = None,
    max_age: int | None = None,
    sort: SkaterSort = "ovr",
    order: Order = "desc",
) -> list[Skater]:
    q = db.query(Skater).filter(Skater.team_id.is_(None))
    if position:
        q = q.filter(Skater.position == position)
    if min_potential is not None:
        q = q.filter(Skater.potential >= min_potential)
    if max_age is not None:
        season_year = _current_season_year(db)
        q = q.filter(Skater.birth_date >= _max_birth_date_for_max_age(season_year, max_age))
    if min_ovr is not None:
        q = q.filter(_skater_ovr_expr() >= min_ovr)

    sort_map = {
        "ovr": _skater_ovr_expr(),
        "potential": Skater.potential,
        "age": Skater.birth_date,
        "position": Skater.position,
    }
    col = sort_map[sort]
    if sort == "age":
        # Older birth_date = younger player; flip semantics so "asc age" = youngest first.
        q = q.order_by(col.desc() if order == "asc" else col.asc())
    else:
        q = q.order_by(col.asc() if order == "asc" else col.desc())
    return q.all()


def list_free_agent_goalies(
    db: Session,
    *,
    min_ovr: int | None = None,
    min_potential: int | None = None,
    max_age: int | None = None,
    sort: GoalieSort = "ovr",
    order: Order = "desc",
) -> list[Goalie]:
    q = db.query(Goalie).filter(Goalie.team_id.is_(None))
    if min_potential is not None:
        q = q.filter(Goalie.potential >= min_potential)
    if max_age is not None:
        season_year = _current_season_year(db)
        q = q.filter(Goalie.birth_date >= _max_birth_date_for_max_age(season_year, max_age))
    if min_ovr is not None:
        q = q.filter(_goalie_ovr_expr() >= min_ovr)

    sort_map = {
        "ovr": _goalie_ovr_expr(),
        "potential": Goalie.potential,
        "age": Goalie.birth_date,
    }
    col = sort_map[sort]
    if sort == "age":
        q = q.order_by(col.desc() if order == "asc" else col.asc())
    else:
        q = q.order_by(col.asc() if order == "asc" else col.desc())
    return q.all()


def _ensure_user_team(db: Session, team_id: int) -> Team:
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise TeamNotFound(f"team {team_id} not found")
    if _current_user_team_id(db) != team_id:
        raise NotUserTeam(f"team {team_id} is not the user team")
    return team


def sign_skater(
    db: Session, team_id: int, skater_id: int, *,
    length: int, salary: int, no_trade_clause: bool = False,
) -> Skater:
    _ensure_user_team(db, team_id)
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    if sk.team_id is not None or contract_service.get_active_contract_for_skater(db, skater_id) is not None:
        raise PlayerNotFreeAgent(f"skater {skater_id} is not a free agent")
    _validate_terms(length, salary)
    sk.team_id = team_id
    contract_service.create_contract_for_skater(
        db, skater_id,
        length=length, signed_season_year=_current_season_year(db),
        salary=salary, no_trade_clause=no_trade_clause,
    )
    db.flush()
    return sk


def sign_goalie(
    db: Session, team_id: int, goalie_id: int, *,
    length: int, salary: int, no_trade_clause: bool = False,
) -> Goalie:
    _ensure_user_team(db, team_id)
    g = db.query(Goalie).filter_by(id=goalie_id).first()
    if not g:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    if g.team_id is not None or contract_service.get_active_contract_for_goalie(db, goalie_id) is not None:
        raise PlayerNotFreeAgent(f"goalie {goalie_id} is not a free agent")
    _validate_terms(length, salary)
    g.team_id = team_id
    contract_service.create_contract_for_goalie(
        db, goalie_id,
        length=length, signed_season_year=_current_season_year(db),
        salary=salary, no_trade_clause=no_trade_clause,
    )
    db.flush()
    return g


def _clear_skater_from_lineup(db: Session, team_id: int, skater_id: int) -> None:
    lu = db.query(Lineup).filter_by(team_id=team_id).first()
    if not lu:
        return
    for col in SKATER_LINEUP_COLS:
        if getattr(lu, col) == skater_id:
            setattr(lu, col, None)


def _clear_goalie_from_lineup(db: Session, team_id: int, goalie_id: int) -> None:
    lu = db.query(Lineup).filter_by(team_id=team_id).first()
    if not lu:
        return
    for col in GOALIE_LINEUP_COLS:
        if getattr(lu, col) == goalie_id:
            setattr(lu, col, None)


def release_skater(db: Session, team_id: int, skater_id: int) -> Skater:
    _ensure_user_team(db, team_id)
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    if sk.team_id != team_id:
        raise PlayerNotOnTeam(f"skater {skater_id} is not on team {team_id}")
    _clear_skater_from_lineup(db, team_id, skater_id)
    active = contract_service.get_active_contract_for_skater(db, skater_id)
    if active is not None:
        contract_service.terminate_contract(db, active, season_year=_current_season_year(db))
    sk.team_id = None
    db.flush()
    return sk


def release_goalie(db: Session, team_id: int, goalie_id: int) -> Goalie:
    _ensure_user_team(db, team_id)
    g = db.query(Goalie).filter_by(id=goalie_id).first()
    if not g:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    if g.team_id != team_id:
        raise PlayerNotOnTeam(f"goalie {goalie_id} is not on team {team_id}")
    _clear_goalie_from_lineup(db, team_id, goalie_id)
    active = contract_service.get_active_contract_for_goalie(db, goalie_id)
    if active is not None:
        contract_service.terminate_contract(db, active, season_year=_current_season_year(db))
    g.team_id = None
    db.flush()
    return g
