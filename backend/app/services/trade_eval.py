"""Pure trade-evaluation primitives (no FastAPI; uses SQLAlchemy session for lookups)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.models import Goalie, Lineup, Skater, Team  # noqa: F401


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


TeamRole = Literal["contender", "middle", "rebuilder"]


def _team_avg_skater_ovr(db: Session, team_id: int) -> float:
    from app.services.generation.players import skater_overall

    skaters = db.query(Skater).filter(Skater.team_id == team_id).all()
    if not skaters:
        return 0.0
    return sum(
        skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)
        for s in skaters
    ) / len(skaters)


def _league_avg_skater_ovr(db: Session) -> float:
    teams = db.query(Team).all()
    if not teams:
        return 0.0
    avgs = [_team_avg_skater_ovr(db, t.id) for t in teams]
    avgs = [a for a in avgs if a > 0]
    return sum(avgs) / len(avgs) if avgs else 0.0


def classify_team_role(db: Session, team_id: int) -> TeamRole:
    team_avg = _team_avg_skater_ovr(db, team_id)
    league_avg = _league_avg_skater_ovr(db)
    diff = team_avg - league_avg
    if diff >= 1.5:
        return "contender"
    if diff <= -1.5:
        return "rebuilder"
    return "middle"


def contender_modifier(role: TeamRole, age: int) -> int:
    if role == "contender":
        return 1 if age <= 32 else -2
    if role == "rebuilder":
        return 2 if age <= 24 else (-2 if age >= 30 else 0)
    return 0


from app.services import contract_service
from app.services.generation.contracts import market_salary
from app.services.generation.players import goalie_overall, skater_overall
from app.services.player_age import age_from_birth_date


CONTRACT_LENGTH_WEIGHT = 0.5
CONTRACT_SALARY_WEIGHT = 0.001


def _skater_ovr(s: Skater) -> int:
    return skater_overall(s.skating, s.shooting, s.passing, s.defense, s.physical)


def _goalie_ovr(g: Goalie) -> int:
    return goalie_overall(g.reflexes, g.positioning, g.rebound_control, g.puck_handling, g.mental)


def _skater_position_need(db: Session, position: str, receiving_team_id: int) -> int:
    same = db.query(Skater).filter(
        Skater.team_id == receiving_team_id, Skater.position == position
    ).count()
    if same <= 1:
        return 3
    if same >= 5:
        return -3
    return 0


def _goalie_need(db: Session, receiving_team_id: int) -> int:
    n = db.query(Goalie).filter(Goalie.team_id == receiving_team_id).count()
    if n <= 1:
        return 3
    if n >= 4:
        return -3
    return 0


def _contract_modifier(
    db: Session, player_type: PlayerType, player_id: int, season_year: int, ovr: int
) -> float:
    if player_type == "skater":
        c = contract_service.get_active_contract_for_skater(db, player_id)
    else:
        c = contract_service.get_active_contract_for_goalie(db, player_id)
    if not c:
        return 0.0
    yrs = max(0, c.expires_after_year - season_year + 1)
    market = market_salary(ovr)
    return (yrs - 2) * CONTRACT_LENGTH_WEIGHT - (c.salary - market) * CONTRACT_SALARY_WEIGHT


def value_skater(db: Session, s: Skater, receiving_team_id: int, season_year: int) -> int:
    age = age_from_birth_date(s.birth_date, season_year)
    ovr = _skater_ovr(s)
    role = classify_team_role(db, receiving_team_id)
    return (
        ovr
        + age_modifier(age)
        + _skater_position_need(db, s.position, receiving_team_id)
        + potential_modifier(s.potential, age)
        + contender_modifier(role, age)
        + int(round(_contract_modifier(db, "skater", s.id, season_year, ovr)))
    )


def value_goalie(db: Session, g: Goalie, receiving_team_id: int, season_year: int) -> int:
    age = age_from_birth_date(g.birth_date, season_year)
    ovr = _goalie_ovr(g)
    role = classify_team_role(db, receiving_team_id)
    return (
        ovr
        + age_modifier(age)
        + _goalie_need(db, receiving_team_id)
        + potential_modifier(g.potential, age)
        + contender_modifier(role, age)
        + int(round(_contract_modifier(db, "goalie", g.id, season_year, ovr)))
    )


@dataclass(frozen=True)
class OfferPlayer:
    player_type: PlayerType
    player_id: int


@dataclass
class RejectionReasonOut:
    code: str
    message: str
    player_type: PlayerType | None = None
    player_id: int | None = None


@dataclass
class WarningOut:
    code: str
    message: str
    team_id: int | None = None


@dataclass
class EvaluateOutcome:
    accepted: bool
    outlook: str  # "accept" | "close" | "reject"
    offered_value: int
    requested_value: int
    rejection_reasons: list[RejectionReasonOut]
    warnings: list[WarningOut]


def evaluate(
    db: Session,
    season_year: int,
    user_team_id: int,
    partner_team_id: int,
    offered: list[OfferPlayer],
    requested: list[OfferPlayer],
) -> EvaluateOutcome:
    def _resolve(p: OfferPlayer):
        if p.player_type == "skater":
            return db.query(Skater).filter(Skater.id == p.player_id).first()
        return db.query(Goalie).filter(Goalie.id == p.player_id).first()

    def _val(p: OfferPlayer, receiving_team_id: int) -> int:
        obj = _resolve(p)
        if p.player_type == "skater":
            return value_skater(db, obj, receiving_team_id, season_year)
        return value_goalie(db, obj, receiving_team_id, season_year)

    def _name(p: OfferPlayer) -> str:
        return _resolve(p).name

    def _ntc(p: OfferPlayer) -> bool:
        if p.player_type == "skater":
            c = contract_service.get_active_contract_for_skater(db, p.player_id)
        else:
            c = contract_service.get_active_contract_for_goalie(db, p.player_id)
        return bool(c and c.no_trade_clause)

    reasons: list[RejectionReasonOut] = []

    # NTC blocks regardless of value
    for p in (*offered, *requested):
        if _ntc(p):
            reasons.append(
                RejectionReasonOut(
                    code="NoTradeClause",
                    message=f"{_name(p)} has a no-trade clause.",
                    player_type=p.player_type,
                    player_id=p.player_id,
                )
            )

    # Top prospect: a *requested* AI skater who is young, high-potential, not yet a star
    for p in requested:
        if p.player_type != "skater":
            continue
        s = _resolve(p)
        age = age_from_birth_date(s.birth_date, season_year)
        ovr = _skater_ovr(s)
        if age <= 23 and s.potential >= 85 and ovr < 80:
            reasons.append(
                RejectionReasonOut(
                    code="TopProspect",
                    message=f"{s.name} is a top prospect — not available.",
                    player_type="skater",
                    player_id=p.player_id,
                )
            )

    # Roster floor (catastrophic) post-trade
    user_skaters = db.query(Skater).filter(Skater.team_id == user_team_id).count()
    user_goalies = db.query(Goalie).filter(Goalie.team_id == user_team_id).count()
    partner_skaters = db.query(Skater).filter(Skater.team_id == partner_team_id).count()
    partner_goalies = db.query(Goalie).filter(Goalie.team_id == partner_team_id).count()

    def _delta(side: list[OfferPlayer], kind: str) -> int:
        return sum(1 for p in side if p.player_type == kind)

    user_skaters_after = user_skaters - _delta(offered, "skater") + _delta(requested, "skater")
    user_goalies_after = user_goalies - _delta(offered, "goalie") + _delta(requested, "goalie")
    partner_skaters_after = partner_skaters + _delta(offered, "skater") - _delta(requested, "skater")
    partner_goalies_after = partner_goalies + _delta(offered, "goalie") - _delta(requested, "goalie")

    if user_skaters_after < 12 or partner_skaters_after < 12:
        reasons.append(RejectionReasonOut(code="RosterFloor", message="Not enough skaters post-trade."))
    if user_goalies_after < 1 or partner_goalies_after < 1:
        reasons.append(RejectionReasonOut(code="RosterFloor", message="Not enough goalies post-trade."))

    # Position need mismatch — partner team would have ≥6 at any single skater position
    pos_after_partner: dict[str, int] = {}
    rows = db.query(Skater.position).filter(Skater.team_id == partner_team_id).all()
    for (pos,) in rows:
        pos_after_partner[pos] = pos_after_partner.get(pos, 0) + 1
    for p in offered:
        if p.player_type == "skater":
            s = _resolve(p)
            pos_after_partner[s.position] = pos_after_partner.get(s.position, 0) + 1
    for p in requested:
        if p.player_type == "skater":
            s = _resolve(p)
            pos_after_partner[s.position] = pos_after_partner.get(s.position, 0) - 1
    for pos, n in pos_after_partner.items():
        if n >= 6:
            reasons.append(
                RejectionReasonOut(
                    code="PositionNeedMismatch",
                    message=f"Partner team would have too many at {pos}.",
                )
            )
            break

    # Value comparison
    offered_values = [_val(p, partner_team_id) for p in offered]
    requested_values = [_val(p, user_team_id) for p in requested]
    offered_sum = sum(offered_values)
    requested_sum = sum(requested_values)
    package_penalty = max(0, len(offered) - len(requested)) * 3
    best_offered = max(offered_values) if offered_values else 0
    best_requested = max(requested_values) if requested_values else 0

    sum_ok = offered_sum >= requested_sum + package_penalty
    floor_ok = best_offered >= best_requested - 5

    if not (sum_ok and floor_ok):
        reasons.append(
            RejectionReasonOut(
                code="ValueTooLow",
                message="Value too low for partner to accept.",
            )
        )

    # Outlook
    if not reasons:
        outlook = "accept"
        accepted = True
    else:
        only_value = all(r.code == "ValueTooLow" for r in reasons)
        close = (
            only_value
            and offered_sum >= requested_sum
            and best_offered >= best_requested - 5
        )
        outlook = "close" if close else "reject"
        accepted = False

    # Warnings (non-blocking)
    warnings: list[WarningOut] = []
    if user_skaters_after < 18 or user_goalies_after < 2:
        warnings.append(
            WarningOut(
                code="RosterBelowActiveFloor",
                message="Your roster will be below the active floor (18 skaters / 2 goalies).",
                team_id=user_team_id,
            )
        )
    if partner_skaters_after < 18 or partner_goalies_after < 2:
        warnings.append(
            WarningOut(
                code="RosterBelowActiveFloor",
                message="Partner roster will be below the active floor.",
                team_id=partner_team_id,
            )
        )

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

    def _in_lineup(team_id: int, p: OfferPlayer) -> bool:
        lu = db.query(Lineup).filter(Lineup.team_id == team_id).first()
        if lu is None:
            return False
        cols = SKATER_LINEUP_COLS if p.player_type == "skater" else GOALIE_LINEUP_COLS
        return any(getattr(lu, c) == p.player_id for c in cols)

    if any(_in_lineup(user_team_id, p) for p in offered) or any(
        _in_lineup(partner_team_id, p) for p in requested
    ):
        warnings.append(
            WarningOut(
                code="LineupSlotsCleared",
                message="Affected lineup slots will be cleared.",
            )
        )

    return EvaluateOutcome(
        accepted=accepted,
        outlook=outlook,
        offered_value=offered_sum,
        requested_value=requested_sum,
        rejection_reasons=reasons,
        warnings=warnings,
    )
