from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import (
    DomainError,
    GoalieNotFound,
    NotUserTeam,
    SeasonAlreadyComplete,
    SkaterNotFound,
    TeamNotFound,
)
from app.models import Goalie, Season, Skater, Team
from app.services import trade_eval
from app.services.free_agents_service import (
    _clear_goalie_from_lineup,
    _clear_skater_from_lineup,
    _current_user_team_id,
)
from app.services.trade_eval import EvaluateOutcome, OfferPlayer


class TradeOfferInvalid(DomainError):
    code = "TradeOfferInvalid"
    status = 400


class TradeWithOwnTeamNotAllowed(DomainError):
    code = "TradeWithOwnTeamNotAllowed"
    status = 422


def _require_active_season(db: Session) -> Season:
    season = db.query(Season).order_by(Season.id.desc()).first()
    if season is None:
        raise NotUserTeam()
    if getattr(season, "status", None) == "complete":
        raise SeasonAlreadyComplete()
    return season


def _load_player(db: Session, p: OfferPlayer):
    if p.player_type == "skater":
        s = db.query(Skater).filter(Skater.id == p.player_id).first()
        if s is None:
            raise SkaterNotFound()
        return s
    g = db.query(Goalie).filter(Goalie.id == p.player_id).first()
    if g is None:
        raise GoalieNotFound()
    return g


def _validate_shape(
    db: Session,
    user_team_id: int,
    partner_team_id: int,
    offered: list[OfferPlayer],
    requested: list[OfferPlayer],
) -> None:
    if not (1 <= len(offered) <= 3) or not (1 <= len(requested) <= 3):
        raise TradeOfferInvalid("Each side must have 1-3 players.")
    seen: set[tuple[str, int]] = set()
    for p in (*offered, *requested):
        key = (p.player_type, p.player_id)
        if key in seen:
            raise TradeOfferInvalid("Duplicate player in offer.")
        seen.add(key)
    if db.query(Team).filter(Team.id == partner_team_id).first() is None:
        raise TeamNotFound()
    if partner_team_id == user_team_id:
        raise TradeWithOwnTeamNotAllowed()
    for p in offered:
        obj = _load_player(db, p)
        if obj.team_id != user_team_id:
            raise TradeOfferInvalid("Offered player must be on the user team.")
    for p in requested:
        obj = _load_player(db, p)
        if obj.team_id != partner_team_id:
            raise TradeOfferInvalid("Requested player must be on the partner team.")


def evaluate_offer(
    db: Session,
    partner_team_id: int,
    offered: list[OfferPlayer],
    requested: list[OfferPlayer],
) -> EvaluateOutcome:
    season = _require_active_season(db)
    user_team_id = _current_user_team_id(db)
    if user_team_id is None:
        raise NotUserTeam()
    _validate_shape(db, user_team_id, partner_team_id, offered, requested)
    return trade_eval.evaluate(
        db,
        season_year=season.year,
        user_team_id=user_team_id,
        partner_team_id=partner_team_id,
        offered=offered,
        requested=requested,
    )


def execute_offer(
    db: Session,
    partner_team_id: int,
    offered: list[OfferPlayer],
    requested: list[OfferPlayer],
) -> tuple[EvaluateOutcome, list[OfferPlayer], list[OfferPlayer]]:
    outcome = evaluate_offer(db, partner_team_id, offered, requested)
    if not outcome.accepted:
        return outcome, [], []
    user_team_id = _current_user_team_id(db)
    assert user_team_id is not None
    for p in offered:
        if p.player_type == "skater":
            _clear_skater_from_lineup(db, user_team_id, p.player_id)
            db.query(Skater).filter(Skater.id == p.player_id).update(
                {"team_id": partner_team_id}
            )
        else:
            _clear_goalie_from_lineup(db, user_team_id, p.player_id)
            db.query(Goalie).filter(Goalie.id == p.player_id).update(
                {"team_id": partner_team_id}
            )
    for p in requested:
        if p.player_type == "skater":
            _clear_skater_from_lineup(db, partner_team_id, p.player_id)
            db.query(Skater).filter(Skater.id == p.player_id).update(
                {"team_id": user_team_id}
            )
        else:
            _clear_goalie_from_lineup(db, partner_team_id, p.player_id)
            db.query(Goalie).filter(Goalie.id == p.player_id).update(
                {"team_id": user_team_id}
            )
    db.flush()
    return outcome, list(requested), list(offered)
