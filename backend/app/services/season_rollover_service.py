import random
from collections import defaultdict

from sqlalchemy.orm import Session

from app.errors import NoActiveSeason, SeasonNotComplete
from app.models import (
    DevelopmentEvent,
    Game,
    Goalie,
    GoalieGameStat,
    Season,
    SeasonProgression,
    Skater,
    SkaterGameStat,
    Standing,
    Team,
)
from app.services.generation.schedule import generate_schedule
from sim.development import (
    GOALIE_ATTRIBUTES,
    SKATER_ATTRIBUTES,
    PlayerDevInput,
    PlayerDevResult,
    develop_player,
)


def _league_skater_ppg(db: Session, season_id: int) -> float:
    rows = (
        db.query(SkaterGameStat)
        .join(Game, SkaterGameStat.game_id == Game.id)
        .filter(Game.season_id == season_id)
        .all()
    )
    if not rows:
        return 0.0
    pts_by_player: dict[int, int] = defaultdict(int)
    gp_by_player: dict[int, int] = defaultdict(int)
    for r in rows:
        pts_by_player[r.skater_id] += (r.goals or 0) + (r.assists or 0)
        gp_by_player[r.skater_id] += 1
    ppg_values = [
        pts_by_player[pid] / gp_by_player[pid]
        for pid in pts_by_player
        if gp_by_player[pid] > 0
    ]
    return sum(ppg_values) / len(ppg_values) if ppg_values else 0.0


def _league_save_pct(db: Session, season_id: int) -> float:
    rows = (
        db.query(GoalieGameStat)
        .join(Game, GoalieGameStat.game_id == Game.id)
        .filter(Game.season_id == season_id)
        .all()
    )
    sa = sum(r.shots_against for r in rows)
    sv = sum(r.saves for r in rows)
    return (sv / sa) if sa else 0.0


def _skater_perf_signal(
    db: Session, season_id: int, skater_id: int, league_ppg: float
) -> float:
    rows = (
        db.query(SkaterGameStat)
        .join(Game, SkaterGameStat.game_id == Game.id)
        .filter(Game.season_id == season_id, SkaterGameStat.skater_id == skater_id)
        .all()
    )
    gp = len(rows)
    if gp == 0 or league_ppg == 0:
        return 0.0
    pts = sum((r.goals or 0) + (r.assists or 0) for r in rows)
    ppg = pts / gp
    gp_weight = min(gp / 20, 1.0)
    s = ((ppg / league_ppg) - 1) * gp_weight
    return max(-1.0, min(1.0, s))


def _goalie_perf_signal(
    db: Session, season_id: int, goalie_id: int, league_sv: float
) -> float:
    rows = (
        db.query(GoalieGameStat)
        .join(Game, GoalieGameStat.game_id == Game.id)
        .filter(Game.season_id == season_id, GoalieGameStat.goalie_id == goalie_id)
        .all()
    )
    gp = len(rows)
    if gp == 0 or league_sv == 0:
        return 0.0
    sa = sum(r.shots_against for r in rows)
    sv = sum(r.saves for r in rows)
    if sa == 0:
        return 0.0
    sv_pct = sv / sa
    gp_weight = min(gp / 10, 1.0)
    s = ((sv_pct - league_sv) / 0.020) * gp_weight
    return max(-1.0, min(1.0, s))


def _apply_skater_development(skater: Skater, result: PlayerDevResult) -> None:
    for attr in SKATER_ATTRIBUTES:
        setattr(skater, attr, result.new_attrs[attr])


def _apply_goalie_development(goalie: Goalie, result: PlayerDevResult) -> None:
    for attr in GOALIE_ATTRIBUTES:
        setattr(goalie, attr, result.new_attrs[attr])


def _persist_progression(
    db: Session,
    *,
    from_season_id: int,
    to_season_id: int,
    player_type: str,
    player_id: int,
    age_before: int,
    age_after: int,
    potential: int,
    development_type: str,
    result: PlayerDevResult,
) -> None:
    sp = SeasonProgression(
        from_season_id=from_season_id,
        to_season_id=to_season_id,
        player_type=player_type,
        player_id=player_id,
        age_before=age_before,
        age_after=age_after,
        overall_before=result.overall_before,
        overall_after=result.overall_after,
        potential=potential,
        development_type=development_type,
        summary_reason=result.summary_reason,
    )
    db.add(sp)
    db.flush()
    for ev in result.events:
        db.add(
            DevelopmentEvent(
                season_progression_id=sp.id,
                attribute=ev.attribute,
                old_value=ev.old_value,
                new_value=ev.new_value,
                delta=ev.delta,
                reason=ev.reason,
            )
        )


def start_next_season(db: Session) -> dict:
    season = (
        db.query(Season)
        .filter(Season.status.in_(["active", "complete"]))
        .order_by(Season.id.desc())
        .first()
    )
    if season is None:
        raise NoActiveSeason("no active or completed season")
    if season.status != "complete":
        raise SeasonNotComplete(
            f"season {season.id} status={season.status!r}; expected 'complete'"
        )
    scheduled = (
        db.query(Game).filter_by(season_id=season.id, status="scheduled").count()
    )
    if scheduled > 0:
        raise SeasonNotComplete(
            f"season {season.id} has {scheduled} scheduled games remaining"
        )

    league_ppg = _league_skater_ppg(db, season.id)
    league_sv = _league_save_pct(db, season.id)

    new_seed = (season.seed * 31 + season.id) & 0x7FFFFFFF
    new_season = Season(
        seed=new_seed,
        user_team_id=season.user_team_id,
        current_matchday=1,
        status="active",
    )
    db.add(new_season)
    db.flush()

    skaters = db.query(Skater).all()
    goalies = db.query(Goalie).all()

    for s in skaters:
        perf = _skater_perf_signal(db, season.id, s.id, league_ppg)
        inp = PlayerDevInput(
            player_id=s.id,
            player_type="skater",
            age=s.age,
            attrs={
                "skating": s.skating,
                "shooting": s.shooting,
                "passing": s.passing,
                "defense": s.defense,
                "physical": s.physical,
            },
            potential=s.potential,
            development_type=s.development_type,
            perf_signal=perf,
        )
        result = develop_player(inp, season_seed=new_seed)
        _persist_progression(
            db,
            from_season_id=season.id,
            to_season_id=new_season.id,
            player_type="skater",
            player_id=s.id,
            age_before=s.age,
            age_after=s.age + 1,
            potential=s.potential,
            development_type=s.development_type,
            result=result,
        )
        _apply_skater_development(s, result)
        s.age += 1

    for g in goalies:
        perf = _goalie_perf_signal(db, season.id, g.id, league_sv)
        inp = PlayerDevInput(
            player_id=g.id,
            player_type="goalie",
            age=g.age,
            attrs={
                "reflexes": g.reflexes,
                "positioning": g.positioning,
                "rebound_control": g.rebound_control,
                "puck_handling": g.puck_handling,
                "mental": g.mental,
            },
            potential=g.potential,
            development_type=g.development_type,
            perf_signal=perf,
        )
        result = develop_player(inp, season_seed=new_seed)
        _persist_progression(
            db,
            from_season_id=season.id,
            to_season_id=new_season.id,
            player_type="goalie",
            player_id=g.id,
            age_before=g.age,
            age_after=g.age + 1,
            potential=g.potential,
            development_type=g.development_type,
            result=result,
        )
        _apply_goalie_development(g, result)
        g.age += 1

    team_ids = [t.id for t in db.query(Team).order_by(Team.id).all()]
    rng = random.Random(new_seed)
    generate_schedule(rng, db, new_season.id, team_ids)
    for tid in team_ids:
        db.add(Standing(team_id=tid, season_id=new_season.id))
    db.flush()

    return {"new_season_id": new_season.id, "season_id": new_season.id}
