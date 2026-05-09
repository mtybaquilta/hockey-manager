from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from sqlalchemy import func

from app.errors import GoalieNotFound, SkaterNotFound
from app.services import contract_service
from app.services.league_service import get_league
from app.services.player_age import age_from_birth_date
from app.models import (
    DevelopmentEvent,
    Game,
    Goalie,
    GoalieGameStat,
    Lineup,
    SeasonProgression,
    Skater,
    SkaterGameStat,
)
from app.schemas.contract import ContractOut
from app.services.free_agents_service import GOALIE_LINEUP_COLS, SKATER_LINEUP_COLS
from app.schemas.career import (
    GoalieCareerOut,
    GoalieSeasonStatsOut,
    SkaterCareerOut,
    SkaterSeasonStatsOut,
)
from app.schemas.development import DevelopmentEventOut, SeasonProgressionOut


class _SkaterAttrs(BaseModel):
    skating: int
    shooting: int
    passing: int
    defense: int
    physical: int


class _GoalieAttrs(BaseModel):
    reflexes: int
    positioning: int
    rebound_control: int
    puck_handling: int
    mental: int


class SkaterTotals(BaseModel):
    games_played: int
    goals: int
    assists: int
    points: int
    shots: int
    shooting_pct: float


class GoalieTotals(BaseModel):
    games_played: int
    shots_against: int
    saves: int
    goals_against: int
    save_pct: float
    gaa: float


class SkaterGameLogRow(BaseModel):
    game_id: int
    matchday: int
    opponent_team_id: int
    is_home: bool
    goals: int
    assists: int
    points: int
    shots: int


class GoalieGameLogRow(BaseModel):
    game_id: int
    matchday: int
    opponent_team_id: int
    is_home: bool
    shots_against: int
    saves: int
    goals_against: int
    save_pct: float


class LineupStatus(BaseModel):
    slot_label: str | None
    special_teams: list[str]


class SkaterTeamRanks(BaseModel):
    points: int | None
    goals: int | None
    assists: int | None
    shots: int | None
    team_skater_count: int


class GoalieTeamRanks(BaseModel):
    save_pct: int | None
    wins: int | None
    games_played: int | None
    team_goalie_count: int


class SkaterDetailOut(BaseModel):
    id: int
    name: str
    age: int
    position: str
    team_id: int | None
    potential: int
    development_type: str
    attributes: _SkaterAttrs
    totals: SkaterTotals
    game_log: list[SkaterGameLogRow]
    lineup_status: LineupStatus
    team_ranks: SkaterTeamRanks
    contract: ContractOut | None = None


class GoalieDetailOut(BaseModel):
    id: int
    name: str
    age: int
    team_id: int | None
    potential: int
    development_type: str
    attributes: _GoalieAttrs
    totals: GoalieTotals
    game_log: list[GoalieGameLogRow]
    lineup_status: LineupStatus
    team_ranks: GoalieTeamRanks
    contract: ContractOut | None = None


_SLOT_LABELS = {
    "line1_lw_id": "Line 1 · LW", "line1_c_id": "Line 1 · C", "line1_rw_id": "Line 1 · RW",
    "line2_lw_id": "Line 2 · LW", "line2_c_id": "Line 2 · C", "line2_rw_id": "Line 2 · RW",
    "line3_lw_id": "Line 3 · LW", "line3_c_id": "Line 3 · C", "line3_rw_id": "Line 3 · RW",
    "line4_lw_id": "Line 4 · LW", "line4_c_id": "Line 4 · C", "line4_rw_id": "Line 4 · RW",
    "pair1_ld_id": "Pair 1 · LD", "pair1_rd_id": "Pair 1 · RD",
    "pair2_ld_id": "Pair 2 · LD", "pair2_rd_id": "Pair 2 · RD",
    "pair3_ld_id": "Pair 3 · LD", "pair3_rd_id": "Pair 3 · RD",
    "starting_goalie_id": "Starter",
    "backup_goalie_id": "Backup",
}


def _skater_slot(lineup: Lineup | None, skater_id: int) -> str | None:
    if lineup is None:
        return None
    for col in SKATER_LINEUP_COLS:
        if getattr(lineup, col) == skater_id:
            return _SLOT_LABELS[col]
    return None


def _goalie_slot(lineup: Lineup | None, goalie_id: int) -> str | None:
    if lineup is None:
        return None
    for col in GOALIE_LINEUP_COLS:
        if getattr(lineup, col) == goalie_id:
            return _SLOT_LABELS[col]
    return None


def _pp_score(s: Skater) -> float:
    return 0.45 * s.shooting + 0.35 * s.passing + 0.2 * s.skating


def _pk_score(s: Skater) -> float:
    return 0.45 * s.defense + 0.3 * s.skating + 0.25 * s.physical


def _skater_special_teams(db: Session, skater: Skater) -> list[str]:
    """Mirror sim.special_teams selection: top-6 forwards by pp_score → PP1/PP2;
    top-4 defensemen by pp_score → PP1/PP2 D; top-2 forwards/D by pk_score → PK."""
    if skater.team_id is None:
        return []
    teammates = db.query(Skater).filter(Skater.team_id == skater.team_id).all()
    forwards = [s for s in teammates if s.position not in ("LD", "RD")]
    defense = [s for s in teammates if s.position in ("LD", "RD")]
    is_fwd = skater.position not in ("LD", "RD")
    pool = forwards if is_fwd else defense
    pp_n = 6 if is_fwd else 4
    pk_n = 2
    units: list[str] = []
    pp_sorted = sorted(pool, key=lambda s: (-_pp_score(s), s.id))
    pp_top = pp_sorted[:pp_n]
    if any(s.id == skater.id for s in pp_top[: pp_n // 2]):
        units.append("PP1")
    elif any(s.id == skater.id for s in pp_top[pp_n // 2:]):
        units.append("PP2")
    pk_sorted = sorted(pool, key=lambda s: (-_pk_score(s), s.id))
    if any(s.id == skater.id for s in pk_sorted[:pk_n]):
        units.append("PK")
    return units


def _skater_lineup_status(db: Session, skater: Skater) -> LineupStatus:
    if skater.team_id is None:
        return LineupStatus(slot_label=None, special_teams=[])
    lineup = db.query(Lineup).filter(Lineup.team_id == skater.team_id).first()
    return LineupStatus(
        slot_label=_skater_slot(lineup, skater.id),
        special_teams=_skater_special_teams(db, skater),
    )


def _goalie_lineup_status(db: Session, goalie: Goalie) -> LineupStatus:
    if goalie.team_id is None:
        return LineupStatus(slot_label=None, special_teams=[])
    lineup = db.query(Lineup).filter(Lineup.team_id == goalie.team_id).first()
    return LineupStatus(slot_label=_goalie_slot(lineup, goalie.id), special_teams=[])


def _rank_or_none(values: list[tuple[int, float]], target_id: int) -> int | None:
    """Given (player_id, value) tuples, return 1-based rank of target by value desc.
    Returns None if target not in the list."""
    sorted_vals = sorted(values, key=lambda kv: (-kv[1], kv[0]))
    for i, (pid, _) in enumerate(sorted_vals, start=1):
        if pid == target_id:
            return i
    return None


def _skater_team_ranks(
    db: Session, skater: Skater, season_id: int
) -> SkaterTeamRanks:
    if skater.team_id is None:
        return SkaterTeamRanks(
            points=None, goals=None, assists=None, shots=None, team_skater_count=0
        )
    rows = (
        db.query(
            SkaterGameStat.skater_id,
            func.coalesce(func.sum(SkaterGameStat.goals), 0).label("g"),
            func.coalesce(func.sum(SkaterGameStat.assists), 0).label("a"),
            func.coalesce(func.sum(SkaterGameStat.shots), 0).label("s"),
        )
        .join(Skater, Skater.id == SkaterGameStat.skater_id)
        .join(Game, SkaterGameStat.game_id == Game.id)
        .filter(Skater.team_id == skater.team_id, Game.season_id == season_id)
        .group_by(SkaterGameStat.skater_id)
        .all()
    )
    if not rows:
        team_size = (
            db.query(Skater).filter(Skater.team_id == skater.team_id).count()
        )
        return SkaterTeamRanks(
            points=None, goals=None, assists=None, shots=None,
            team_skater_count=team_size,
        )
    goals = [(r.skater_id, float(r.g)) for r in rows]
    assists = [(r.skater_id, float(r.a)) for r in rows]
    points = [(r.skater_id, float(r.g + r.a)) for r in rows]
    shots = [(r.skater_id, float(r.s)) for r in rows]
    return SkaterTeamRanks(
        points=_rank_or_none(points, skater.id),
        goals=_rank_or_none(goals, skater.id),
        assists=_rank_or_none(assists, skater.id),
        shots=_rank_or_none(shots, skater.id),
        team_skater_count=len(rows),
    )


def _goalie_team_ranks(
    db: Session, goalie: Goalie, season_id: int
) -> GoalieTeamRanks:
    if goalie.team_id is None:
        return GoalieTeamRanks(
            save_pct=None, wins=None, games_played=None, team_goalie_count=0
        )
    rows = (
        db.query(
            GoalieGameStat.goalie_id,
            func.count(GoalieGameStat.id).label("gp"),
            func.coalesce(func.sum(GoalieGameStat.shots_against), 0).label("sa"),
            func.coalesce(func.sum(GoalieGameStat.saves), 0).label("sv"),
        )
        .join(Goalie, Goalie.id == GoalieGameStat.goalie_id)
        .join(Game, GoalieGameStat.game_id == Game.id)
        .filter(Goalie.team_id == goalie.team_id, Game.season_id == season_id)
        .group_by(GoalieGameStat.goalie_id)
        .all()
    )
    if not rows:
        team_size = db.query(Goalie).filter(Goalie.team_id == goalie.team_id).count()
        return GoalieTeamRanks(
            save_pct=None, wins=None, games_played=None, team_goalie_count=team_size
        )
    sv_pct = [(r.goalie_id, (r.sv / r.sa) if r.sa else 0.0) for r in rows]
    gp = [(r.goalie_id, float(r.gp)) for r in rows]
    return GoalieTeamRanks(
        save_pct=_rank_or_none(sv_pct, goalie.id),
        wins=None,
        games_played=_rank_or_none(gp, goalie.id),
        team_goalie_count=len(rows),
    )


router = APIRouter(prefix="/players", tags=["players"])


@router.get("/skater/{skater_id}", response_model=SkaterDetailOut)
def get_skater(skater_id: int, db: Session = Depends(get_db)):
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    season = get_league(db)
    rows = (
        db.query(SkaterGameStat, Game)
        .join(Game, SkaterGameStat.game_id == Game.id)
        .filter(SkaterGameStat.skater_id == skater_id, Game.season_id == season.id)
        .order_by(Game.matchday, Game.id)
        .all()
    )
    log: list[SkaterGameLogRow] = []
    g_total = a_total = s_total = 0
    for stat, gm in rows:
        is_home = gm.home_team_id == sk.team_id
        opp = gm.away_team_id if is_home else gm.home_team_id
        log.append(
            SkaterGameLogRow(
                game_id=gm.id,
                matchday=gm.matchday,
                opponent_team_id=opp,
                is_home=is_home,
                goals=stat.goals,
                assists=stat.assists,
                points=stat.goals + stat.assists,
                shots=stat.shots,
            )
        )
        g_total += stat.goals
        a_total += stat.assists
        s_total += stat.shots
    gp = len(log)
    totals = SkaterTotals(
        games_played=gp,
        goals=g_total,
        assists=a_total,
        points=g_total + a_total,
        shots=s_total,
        shooting_pct=(g_total / s_total) if s_total else 0.0,
    )
    contract = contract_service.get_active_contract_for_skater(db, sk.id)
    return SkaterDetailOut(
        id=sk.id,
        name=sk.name,
        age=age_from_birth_date(sk.birth_date, season.year),
        position=sk.position,
        team_id=sk.team_id,
        potential=sk.potential,
        development_type=sk.development_type,
        attributes=_SkaterAttrs(
            skating=sk.skating,
            shooting=sk.shooting,
            passing=sk.passing,
            defense=sk.defense,
            physical=sk.physical,
        ),
        totals=totals,
        game_log=log,
        lineup_status=_skater_lineup_status(db, sk),
        team_ranks=_skater_team_ranks(db, sk, season.id),
        contract=ContractOut.model_validate(contract) if contract else None,
    )


@router.get("/goalie/{goalie_id}", response_model=GoalieDetailOut)
def get_goalie(goalie_id: int, db: Session = Depends(get_db)):
    gk = db.query(Goalie).filter_by(id=goalie_id).first()
    if not gk:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    season = get_league(db)
    rows = (
        db.query(GoalieGameStat, Game)
        .join(Game, GoalieGameStat.game_id == Game.id)
        .filter(GoalieGameStat.goalie_id == goalie_id, Game.season_id == season.id)
        .order_by(Game.matchday, Game.id)
        .all()
    )
    log: list[GoalieGameLogRow] = []
    sa_total = sv_total = ga_total = 0
    for stat, gm in rows:
        is_home = gm.home_team_id == gk.team_id
        opp = gm.away_team_id if is_home else gm.home_team_id
        log.append(
            GoalieGameLogRow(
                game_id=gm.id,
                matchday=gm.matchday,
                opponent_team_id=opp,
                is_home=is_home,
                shots_against=stat.shots_against,
                saves=stat.saves,
                goals_against=stat.goals_against,
                save_pct=(stat.saves / stat.shots_against) if stat.shots_against else 0.0,
            )
        )
        sa_total += stat.shots_against
        sv_total += stat.saves
        ga_total += stat.goals_against
    gp = len(log)
    totals = GoalieTotals(
        games_played=gp,
        shots_against=sa_total,
        saves=sv_total,
        goals_against=ga_total,
        save_pct=(sv_total / sa_total) if sa_total else 0.0,
        gaa=(ga_total / gp) if gp else 0.0,
    )
    contract = contract_service.get_active_contract_for_goalie(db, gk.id)
    return GoalieDetailOut(
        id=gk.id,
        name=gk.name,
        age=age_from_birth_date(gk.birth_date, season.year),
        team_id=gk.team_id,
        potential=gk.potential,
        development_type=gk.development_type,
        attributes=_GoalieAttrs(
            reflexes=gk.reflexes,
            positioning=gk.positioning,
            rebound_control=gk.rebound_control,
            puck_handling=gk.puck_handling,
            mental=gk.mental,
        ),
        totals=totals,
        game_log=log,
        lineup_status=_goalie_lineup_status(db, gk),
        team_ranks=_goalie_team_ranks(db, gk, season.id),
        contract=ContractOut.model_validate(contract) if contract else None,
    )


def _build_player_history(
    db: Session, player_type: str, player_id: int, name: str, team_id: int
) -> list[SeasonProgressionOut]:
    rows = (
        db.query(SeasonProgression)
        .filter_by(player_type=player_type, player_id=player_id)
        .order_by(SeasonProgression.to_season_id.desc())
        .all()
    )
    history: list[SeasonProgressionOut] = []
    for sp in rows:
        events = (
            db.query(DevelopmentEvent)
            .filter_by(season_progression_id=sp.id)
            .order_by(DevelopmentEvent.id)
            .all()
        )
        history.append(
            SeasonProgressionOut(
                player_type=sp.player_type,
                player_id=sp.player_id,
                player_name=name,
                team_id=team_id,
                age_before=sp.age_before,
                age_after=sp.age_after,
                overall_before=sp.overall_before,
                overall_after=sp.overall_after,
                potential=sp.potential,
                development_type=sp.development_type,
                summary_reason=sp.summary_reason,
                events=[
                    DevelopmentEventOut(
                        attribute=e.attribute,
                        old_value=e.old_value,
                        new_value=e.new_value,
                        delta=e.delta,
                        reason=e.reason,
                    )
                    for e in events
                ],
            )
        )
    return history


@router.get("/skater/{skater_id}/development")
def get_skater_development(skater_id: int, db: Session = Depends(get_db)):
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    history = _build_player_history(db, "skater", sk.id, sk.name, sk.team_id)
    return {
        "player_id": sk.id,
        "name": sk.name,
        "history": [h.model_dump() for h in history],
    }


@router.get("/goalie/{goalie_id}/development")
def get_goalie_development(goalie_id: int, db: Session = Depends(get_db)):
    gk = db.query(Goalie).filter_by(id=goalie_id).first()
    if not gk:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    history = _build_player_history(db, "goalie", gk.id, gk.name, gk.team_id)
    return {
        "player_id": gk.id,
        "name": gk.name,
        "history": [h.model_dump() for h in history],
    }


@router.get("/skater/{skater_id}/career", response_model=SkaterCareerOut)
def get_skater_career(skater_id: int, db: Session = Depends(get_db)):
    sk = db.query(Skater).filter_by(id=skater_id).first()
    if not sk:
        raise SkaterNotFound(f"skater {skater_id} not found")
    rows = (
        db.query(
            Game.season_id.label("season_id"),
            func.count(SkaterGameStat.id).label("gp"),
            func.coalesce(func.sum(SkaterGameStat.goals), 0).label("g"),
            func.coalesce(func.sum(SkaterGameStat.assists), 0).label("a"),
            func.coalesce(func.sum(SkaterGameStat.shots), 0).label("sog"),
        )
        .join(Game, SkaterGameStat.game_id == Game.id)
        .filter(SkaterGameStat.skater_id == skater_id)
        .group_by(Game.season_id)
        .order_by(Game.season_id)
        .all()
    )
    by_season = [
        SkaterSeasonStatsOut(
            season_id=r.season_id,
            gp=r.gp,
            g=r.g,
            a=r.a,
            pts=r.g + r.a,
            sog=r.sog,
        )
        for r in rows
    ]
    totals = SkaterSeasonStatsOut(
        season_id=0,
        gp=sum(s.gp for s in by_season),
        g=sum(s.g for s in by_season),
        a=sum(s.a for s in by_season),
        pts=sum(s.pts for s in by_season),
        sog=sum(s.sog for s in by_season),
    )
    return SkaterCareerOut(
        player_id=sk.id, name=sk.name, by_season=by_season, totals=totals
    )


@router.get("/goalie/{goalie_id}/career", response_model=GoalieCareerOut)
def get_goalie_career(goalie_id: int, db: Session = Depends(get_db)):
    gk = db.query(Goalie).filter_by(id=goalie_id).first()
    if not gk:
        raise GoalieNotFound(f"goalie {goalie_id} not found")
    rows = (
        db.query(
            Game.season_id.label("season_id"),
            func.count(GoalieGameStat.id).label("gp"),
            func.coalesce(func.sum(GoalieGameStat.shots_against), 0).label("sa"),
            func.coalesce(func.sum(GoalieGameStat.saves), 0).label("sv"),
            func.coalesce(func.sum(GoalieGameStat.goals_against), 0).label("ga"),
        )
        .join(Game, GoalieGameStat.game_id == Game.id)
        .filter(GoalieGameStat.goalie_id == goalie_id)
        .group_by(Game.season_id)
        .order_by(Game.season_id)
        .all()
    )
    by_season = [
        GoalieSeasonStatsOut(
            season_id=r.season_id,
            gp=r.gp,
            shots_against=r.sa,
            saves=r.sv,
            goals_against=r.ga,
            sv_pct=(r.sv / r.sa) if r.sa else 0.0,
        )
        for r in rows
    ]
    total_sa = sum(s.shots_against for s in by_season)
    total_sv = sum(s.saves for s in by_season)
    totals = GoalieSeasonStatsOut(
        season_id=0,
        gp=sum(s.gp for s in by_season),
        shots_against=total_sa,
        saves=total_sv,
        goals_against=sum(s.goals_against for s in by_season),
        sv_pct=(total_sv / total_sa) if total_sa else 0.0,
    )
    return GoalieCareerOut(
        player_id=gk.id, name=gk.name, by_season=by_season, totals=totals
    )
