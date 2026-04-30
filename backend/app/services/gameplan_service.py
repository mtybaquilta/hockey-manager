import random

from sqlalchemy.orm import Session

from app.errors import GameplanInvalid, NotUserTeam, TeamNotFound
from app.models import Season, Team, TeamGameplan

ALLOWED_STYLES = ("balanced", "offensive", "defensive", "physical")
ALLOWED_LINE_USAGES = ("balanced", "ride_top_lines", "roll_all_lines")

_STYLE_WEIGHTS = [
    ("balanced", 0.50),
    ("offensive", 0.20),
    ("defensive", 0.20),
    ("physical", 0.10),
]
_LINE_USAGE_WEIGHTS = [
    ("balanced", 0.60),
    ("ride_top_lines", 0.25),
    ("roll_all_lines", 0.15),
]


def _sample(rng: random.Random, weighted: list[tuple[str, float]]) -> str:
    r = rng.random()
    acc = 0.0
    for name, w in weighted:
        acc += w
        if r < acc:
            return name
    return weighted[-1][0]


def _validate(style: str, line_usage: str) -> None:
    if style not in ALLOWED_STYLES:
        raise GameplanInvalid(f"unknown style {style!r}")
    if line_usage not in ALLOWED_LINE_USAGES:
        raise GameplanInvalid(f"unknown line_usage {line_usage!r}")


def _current_user_team_id(db: Session) -> int | None:
    season = db.query(Season).order_by(Season.id.desc()).first()
    return season.user_team_id if season else None


def get_team_gameplan(db: Session, team_id: int) -> TeamGameplan:
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise TeamNotFound(f"team {team_id} not found")
    gp = db.query(TeamGameplan).filter_by(team_id=team_id).first()
    if not gp:
        # Self-heal: insert a balanced/balanced row if missing.
        gp = TeamGameplan(team_id=team_id, style="balanced", line_usage="balanced")
        db.add(gp)
        db.flush()
    return gp


def update_user_team_gameplan(
    db: Session, team_id: int, style: str, line_usage: str
) -> TeamGameplan:
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise TeamNotFound(f"team {team_id} not found")
    if _current_user_team_id(db) != team_id:
        raise NotUserTeam(f"team {team_id} is not the user team")
    _validate(style, line_usage)
    gp = get_team_gameplan(db, team_id)
    gp.style = style
    gp.line_usage = line_usage
    db.flush()
    return gp


def is_editable(db: Session, team_id: int) -> bool:
    return _current_user_team_id(db) == team_id


def generate_gameplans_for_league(
    rng: random.Random, db: Session, team_ids: list[int], user_team_id: int | None
) -> None:
    """Idempotent. Wipes existing rows for the supplied team_ids and inserts
    fresh gameplans. The user team always gets (balanced, balanced)."""
    if team_ids:
        db.query(TeamGameplan).filter(TeamGameplan.team_id.in_(team_ids)).delete(
            synchronize_session=False
        )
    for tid in team_ids:
        if tid == user_team_id:
            db.add(TeamGameplan(team_id=tid, style="balanced", line_usage="balanced"))
        else:
            db.add(
                TeamGameplan(
                    team_id=tid,
                    style=_sample(rng, _STYLE_WEIGHTS),
                    line_usage=_sample(rng, _LINE_USAGE_WEIGHTS),
                )
            )
    db.flush()
