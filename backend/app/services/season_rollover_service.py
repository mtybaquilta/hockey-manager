import random
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import NoActiveSeason, OffseasonRequired
from app.models import (
    DevelopmentEvent,
    Game,
    Goalie,
    GoalieGameStat,
    Lineup,
    Season,
    SeasonProgression,
    Skater,
    SkaterGameStat,
    Standing,
    Team,
)
from app.services import contract_service
from app.services.free_agents_service import (
    GOALIE_LINEUP_COLS,
    SKATER_LINEUP_COLS,
    _clear_goalie_from_lineup,
    _clear_skater_from_lineup,
)
from app.services.generation.schedule import generate_schedule
from app.services.player_age import age_from_birth_date
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


def _refill_lineups(db: Session) -> None:
    """Replace any None slots in each team's lineup with available roster
    players. Used after rollover, when expired-contract players have been
    cleared from their lineup slots."""
    teams = db.query(Team).all()
    for team in teams:
        lu = db.query(Lineup).filter_by(team_id=team.id).first()
        if not lu:
            continue
        skaters = db.query(Skater).filter_by(team_id=team.id).all()
        goalies = db.query(Goalie).filter_by(team_id=team.id).all()
        used_skaters = {getattr(lu, c) for c in SKATER_LINEUP_COLS if getattr(lu, c) is not None}
        used_goalies = {getattr(lu, c) for c in GOALIE_LINEUP_COLS if getattr(lu, c) is not None}
        by_pos: dict[str, list[Skater]] = {}
        for s in skaters:
            by_pos.setdefault(s.position, []).append(s)
        for pool in by_pos.values():
            pool.sort(key=lambda s: -(s.skating + s.shooting + s.passing + s.defense + s.physical))
        free_goalies = sorted(
            [g for g in goalies if g.id not in used_goalies],
            key=lambda g: -(g.reflexes + g.positioning + g.rebound_control + g.puck_handling + g.mental),
        )

        col_to_pos = {
            "line1_lw_id": "LW", "line1_c_id": "C", "line1_rw_id": "RW",
            "line2_lw_id": "LW", "line2_c_id": "C", "line2_rw_id": "RW",
            "line3_lw_id": "LW", "line3_c_id": "C", "line3_rw_id": "RW",
            "line4_lw_id": "LW", "line4_c_id": "C", "line4_rw_id": "RW",
            "pair1_ld_id": "LD", "pair1_rd_id": "RD",
            "pair2_ld_id": "LD", "pair2_rd_id": "RD",
            "pair3_ld_id": "LD", "pair3_rd_id": "RD",
        }
        for col in SKATER_LINEUP_COLS:
            if getattr(lu, col) is not None:
                continue
            pos = col_to_pos[col]
            cands = [s for s in by_pos.get(pos, []) if s.id not in used_skaters]
            if not cands:
                # Fall back to any unused skater.
                for fallback_pos, pool in by_pos.items():
                    cands = [s for s in pool if s.id not in used_skaters]
                    if cands:
                        break
            if cands:
                pick = cands[0]
                setattr(lu, col, pick.id)
                used_skaters.add(pick.id)

        for col in GOALIE_LINEUP_COLS:
            if getattr(lu, col) is not None:
                continue
            if free_goalies:
                pick = free_goalies.pop(0)
                setattr(lu, col, pick.id)
    db.flush()


def start_next_season(db: Session) -> dict:
    season = (
        db.execute(select(Season).order_by(Season.id.desc()).limit(1))
        .scalars()
        .first()
    )
    if season is None:
        raise NoActiveSeason("no active season")
    if season.phase != "offseason":
        raise OffseasonRequired(
            f"season {season.id} phase={season.phase!r}; expected 'offseason'"
        )

    league_ppg = _league_skater_ppg(db, season.id)
    league_sv = _league_save_pct(db, season.id)

    new_seed = (season.seed * 31 + season.id) & 0x7FFFFFFF
    new_year = season.year + 1
    new_season = Season(
        seed=new_seed,
        current_matchday=1,
        status="active",
        phase="regular_season",
        year=new_year,
    )
    db.add(new_season)
    db.flush()

    skaters = db.query(Skater).all()
    goalies = db.query(Goalie).all()

    for s in skaters:
        age_before = age_from_birth_date(s.birth_date, season.year)
        age_after = age_from_birth_date(s.birth_date, new_year)
        perf = _skater_perf_signal(db, season.id, s.id, league_ppg)
        inp = PlayerDevInput(
            player_id=s.id,
            player_type="skater",
            age=age_before,
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
            age_before=age_before,
            age_after=age_after,
            potential=s.potential,
            development_type=s.development_type,
            result=result,
        )
        _apply_skater_development(s, result)

    for g in goalies:
        age_before = age_from_birth_date(g.birth_date, season.year)
        age_after = age_from_birth_date(g.birth_date, new_year)
        perf = _goalie_perf_signal(db, season.id, g.id, league_sv)
        inp = PlayerDevInput(
            player_id=g.id,
            player_type="goalie",
            age=age_before,
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
            age_before=age_before,
            age_after=age_after,
            potential=g.potential,
            development_type=g.development_type,
            result=result,
        )
        _apply_goalie_development(g, result)

    expired_players = contract_service.expire_contracts_through_year(
        db, new_season_year=new_year
    )
    for player_type, player_id in expired_players:
        if player_type == "skater":
            sk = db.query(Skater).filter_by(id=player_id).one()
            if sk.team_id is not None:
                _clear_skater_from_lineup(db, sk.team_id, sk.id)
                sk.team_id = None
        else:
            gl = db.query(Goalie).filter_by(id=player_id).one()
            if gl.team_id is not None:
                _clear_goalie_from_lineup(db, gl.team_id, gl.id)
                gl.team_id = None

    _refill_lineups(db)

    team_ids = [t.id for t in db.query(Team).order_by(Team.id).all()]
    rng = random.Random(new_seed)
    generate_schedule(rng, db, new_season.id, team_ids)
    for tid in team_ids:
        db.add(Standing(team_id=tid, season_id=new_season.id))

    season.status = "complete"
    from app.services import manager_profile_service

    mgr = manager_profile_service.get_active_profile(db)
    if mgr is not None:
        mgr.seasons_completed += 1
    db.flush()

    return {
        "new_season_id": new_season.id,
        "season_id": new_season.id,
        "from_season_id": season.id,
        "to_season_id": new_season.id,
        "new_year": new_year,
        "expired_player_count": len(expired_players),
    }
