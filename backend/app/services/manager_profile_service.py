from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import DomainError, TeamNotFound
from app.models import ManagerProfile, Team


class ManagerProfileNotFound(DomainError):
    code = "ManagerProfileNotFound"
    status = 404


class ManagerNameInvalid(DomainError):
    code = "ManagerNameInvalid"
    status = 422


def _validate_name(name: str) -> str:
    name = name.strip()
    if not (1 <= len(name) <= 64):
        raise ManagerNameInvalid("name must be 1-64 characters")
    return name


def get_active_profile(db: Session) -> ManagerProfile | None:
    """Return the most recently created profile, if any.

    With multiple profiles supported in schema but no UI for switching yet,
    we treat the latest profile as the active one.
    """
    return db.query(ManagerProfile).order_by(ManagerProfile.id.desc()).first()


def require_active_profile(db: Session) -> ManagerProfile:
    p = get_active_profile(db)
    if p is None:
        raise ManagerProfileNotFound("no manager profile exists")
    return p


def current_team_id(db: Session) -> int | None:
    p = get_active_profile(db)
    return p.current_team_id if p else None


def create_profile(db: Session, *, name: str) -> ManagerProfile:
    p = ManagerProfile(name=_validate_name(name))
    db.add(p)
    db.flush()
    return p


def set_team(db: Session, profile_id: int, team_id: int) -> ManagerProfile:
    p = db.query(ManagerProfile).filter_by(id=profile_id).first()
    if p is None:
        raise ManagerProfileNotFound(f"manager profile {profile_id} not found")
    team = db.query(Team).filter_by(id=team_id).first()
    if team is None:
        raise TeamNotFound(f"team {team_id} not found")
    p.current_team_id = team_id
    db.flush()
    return p
