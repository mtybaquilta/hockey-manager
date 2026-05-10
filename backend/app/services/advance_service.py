from sqlalchemy.orm import Session

from app.errors import LeagueNotFound, LineupIncomplete, SeasonAlreadyComplete
from app.models import (
    Game,
    GameEvent,
    Goalie,
    GoalieGameStat,
    Lineup,
    ManagerProfile,
    PlayoffSeries,
    Season,
    Skater,
    SkaterGameStat,
    Standing,
    TeamGameplan,
)
from app.services import manager_profile_service, playoff_service
from sim.engine import simulate_game
from sim.models import (
    Position,
    ResultType,
    SimGameInput,
    SimGameplan,
    SimGoalie,
    SimLine,
    SimSkater,
    SimTeamInput,
    SimTeamLineup,
)
from sim.seed import derive_game_seed

LINE_FWD_SLOTS = [
    ("line1_lw_id", "line1_c_id", "line1_rw_id"),
    ("line2_lw_id", "line2_c_id", "line2_rw_id"),
    ("line3_lw_id", "line3_c_id", "line3_rw_id"),
    ("line4_lw_id", "line4_c_id", "line4_rw_id"),
]
PAIR_DEF_SLOTS = [
    ("pair1_ld_id", "pair1_rd_id"),
    ("pair2_ld_id", "pair2_rd_id"),
    ("pair3_ld_id", "pair3_rd_id"),
]


def _gameplan_for(db: Session, team_id: int) -> SimGameplan:
    gp = db.query(TeamGameplan).filter_by(team_id=team_id).first()
    if gp is None:
        return SimGameplan(style="balanced", line_usage="balanced")
    return SimGameplan(style=gp.style, line_usage=gp.line_usage)


def _to_sim_skater(s: Skater) -> SimSkater:
    return SimSkater(
        id=s.id,
        position=Position(s.position),
        skating=s.skating,
        shooting=s.shooting,
        passing=s.passing,
        defense=s.defense,
        physical=s.physical,
    )


def _to_sim_goalie(g: Goalie) -> SimGoalie:
    return SimGoalie(
        id=g.id,
        reflexes=g.reflexes,
        positioning=g.positioning,
        rebound_control=g.rebound_control,
        puck_handling=g.puck_handling,
        mental=g.mental,
    )


_SKATER_POS_BY_SLOT: dict[str, str] = {
    "line1_lw_id": "LW", "line2_lw_id": "LW", "line3_lw_id": "LW", "line4_lw_id": "LW",
    "line1_c_id": "C", "line2_c_id": "C", "line3_c_id": "C", "line4_c_id": "C",
    "line1_rw_id": "RW", "line2_rw_id": "RW", "line3_rw_id": "RW", "line4_rw_id": "RW",
    "pair1_ld_id": "LD", "pair2_ld_id": "LD", "pair3_ld_id": "LD",
    "pair1_rd_id": "RD", "pair2_rd_id": "RD", "pair3_rd_id": "RD",
}


def _build_lineup(db: Session, team_id: int) -> SimTeamLineup:
    """Build a SimTeamLineup, resolving any missing slot ids (None) by falling
    back to the next-best roster skater at the same position, then to any
    unused skater on the team. As a last resort, the slot reuses an already-
    placed skater so the simulator always has a full lineup. This makes the
    sim resilient to partially-saved lineups after expirations or trades.
    """
    lu = db.query(Lineup).filter_by(team_id=team_id).one()
    roster = db.query(Skater).filter_by(team_id=team_id).all()
    by_pos: dict[str, list[Skater]] = {}
    for s in roster:
        by_pos.setdefault(s.position, []).append(s)
    for pool in by_pos.values():
        pool.sort(
            key=lambda s: -(s.skating + s.shooting + s.passing + s.defense + s.physical)
        )
    by_id = {s.id: s for s in roster}

    used: set[int] = set()
    resolved: dict[str, Skater] = {}

    # First pass: resolve every slot with an assigned id. Drop ids that no
    # longer point to a roster skater (stale/traded), so the fallback path
    # below kicks in for those slots.
    all_slots = list(_SKATER_POS_BY_SLOT.keys())
    for slot in all_slots:
        sid = getattr(lu, slot)
        if sid is None:
            continue
        sk = by_id.get(sid)
        if sk is None:
            continue
        resolved[slot] = sk
        used.add(sk.id)

    # Second pass: fill empty slots from the position pool first, then any
    # unused skater. If still nothing, repeat an already-placed skater.
    for slot in all_slots:
        if slot in resolved:
            continue
        pos = _SKATER_POS_BY_SLOT[slot]
        cand = next((s for s in by_pos.get(pos, []) if s.id not in used), None)
        if cand is None:
            for pool in by_pos.values():
                cand = next((s for s in pool if s.id not in used), None)
                if cand is not None:
                    break
        if cand is None:
            # Roster too small even with reuse — repeat the first resolved skater.
            cand = next(iter(resolved.values()), None)
        if cand is None:
            raise LeagueNotFound(
                f"team {team_id} has no skaters available to ice a lineup"
            )
        resolved[slot] = cand
        used.add(cand.id)

    fwd_lines = tuple(
        SimLine(skaters=tuple(_to_sim_skater(resolved[c]) for c in trio))
        for trio in LINE_FWD_SLOTS
    )
    pairs = tuple(
        SimLine(skaters=tuple(_to_sim_skater(resolved[c]) for c in pair))
        for pair in PAIR_DEF_SLOTS
    )

    # Goalies: prefer the saved starter, then backup, then any team goalie.
    goalie = None
    if lu.starting_goalie_id is not None:
        goalie = db.query(Goalie).filter_by(id=lu.starting_goalie_id).first()
    if goalie is None and lu.backup_goalie_id is not None:
        goalie = db.query(Goalie).filter_by(id=lu.backup_goalie_id).first()
    if goalie is None:
        goalie = db.query(Goalie).filter_by(team_id=team_id).first()
    if goalie is None:
        raise LeagueNotFound(f"team {team_id} has no goalie available")
    return SimTeamLineup(
        forward_lines=fwd_lines,
        defense_pairs=pairs,
        starting_goalie=_to_sim_goalie(goalie),
    )


def _apply_standing(
    stand_by_team: dict[int, Standing],
    home_id: int,
    away_id: int,
    home: int,
    away: int,
    result_type: ResultType,
    manager: "ManagerProfile | None" = None,
) -> None:
    sh, sa = stand_by_team[home_id], stand_by_team[away_id]
    sh.games_played += 1
    sa.games_played += 1
    sh.goals_for += home
    sh.goals_against += away
    sa.goals_for += away
    sa.goals_against += home
    if home > away:
        sh.wins += 1
        sh.points += 2
        if result_type == ResultType.REG:
            sa.losses += 1
        else:
            sa.ot_losses += 1
            sa.points += 1
    else:
        sa.wins += 1
        sa.points += 2
        if result_type == ResultType.REG:
            sh.losses += 1
        else:
            sh.ot_losses += 1
            sh.points += 1

    if manager is not None and manager.current_team_id in (home_id, away_id):
        user_won = (
            (home > away and manager.current_team_id == home_id)
            or (away > home and manager.current_team_id == away_id)
        )
        if user_won:
            manager.career_wins += 1
        elif result_type == ResultType.REG:
            manager.career_losses += 1
        else:
            manager.career_ot_losses += 1


def _simulate_game_row(
    db: Session,
    g: Game,
    season: Season,
    standings: dict[int, Standing],
    manager: ManagerProfile | None = None,
) -> int:
    """Simulate one game row, persist events/stats, update standings if RS.
    Returns the game id."""
    home_lu = _build_lineup(db, g.home_team_id)
    away_lu = _build_lineup(db, g.away_team_id)
    seed = derive_game_seed(season.seed, g.id)
    home_gp = _gameplan_for(db, g.home_team_id)
    away_gp = _gameplan_for(db, g.away_team_id)
    result = simulate_game(
        SimGameInput(
            home=SimTeamInput(lineup=home_lu, gameplan=home_gp),
            away=SimTeamInput(lineup=away_lu, gameplan=away_gp),
            seed=seed,
        )
    )

    g.status = "simulated"
    g.home_score = result.home_score
    g.away_score = result.away_score
    g.home_shots = result.home_shots
    g.away_shots = result.away_shots
    g.result_type = result.result_type.value
    g.seed = seed

    for e in result.events:
        db.add(
            GameEvent(
                game_id=g.id,
                tick=e.tick,
                period=e.period,
                kind=e.kind.value,
                strength=e.strength.value if e.strength is not None else None,
                team_id=g.home_team_id if e.team_is_home else g.away_team_id,
                primary_skater_id=e.primary_skater_id,
                assist1_id=e.assist1_id,
                assist2_id=e.assist2_id,
                goalie_id=e.goalie_id,
                penalty_duration_ticks=e.penalty_duration_ticks,
                shot_quality=e.shot_quality.value if e.shot_quality is not None else None,
            )
        )
    for ss in result.skater_stats:
        db.add(
            SkaterGameStat(
                game_id=g.id,
                skater_id=ss.skater_id,
                goals=ss.goals,
                assists=ss.assists,
                shots=ss.shots,
            )
        )
    for gs in result.goalie_stats:
        db.add(
            GoalieGameStat(
                game_id=g.id,
                goalie_id=gs.goalie_id,
                shots_against=gs.shots_against,
                saves=gs.saves,
                goals_against=gs.goals_against,
            )
        )
    if g.phase == "regular_season":
        _apply_standing(
            standings,
            g.home_team_id,
            g.away_team_id,
            result.home_score,
            result.away_score,
            result.result_type,
            manager=manager,
        )
    return g.id


def _advance_playoffs(
    db: Session, season: Season, affected_series_ids: set[int]
) -> None:
    """After playoff games on the just-completed matchday have been simmed,
    recount each affected series, then either schedule next series games on
    the new current_matchday, build the next round, or finish the season."""
    for sid in affected_series_ids:
        series = db.query(PlayoffSeries).filter_by(id=sid).one()
        playoff_service.recompute_series_state(db, series)
    db.flush()

    current_round = playoff_service.latest_round(db, season.id)
    assert current_round is not None  # we are in playoffs phase
    active = (
        db.query(PlayoffSeries)
        .filter_by(season_id=season.id, round=current_round, status="active")
        .order_by(PlayoffSeries.bracket_slot)
        .all()
    )
    if active:
        for s in active:
            playoff_service.schedule_next_game_for_series(
                db, s, season.id, season.current_matchday
            )
        db.flush()
        return

    # Round complete.
    if current_round == playoff_service.ROUND_FINAL:
        final = (
            db.query(PlayoffSeries)
            .filter_by(season_id=season.id, round=playoff_service.ROUND_FINAL)
            .first()
        )
        season.champion_team_id = final.winner_team_id if final else None
        season.phase = "offseason"
        manager = manager_profile_service.get_active_profile(db)
        if (
            manager is not None
            and manager.current_team_id is not None
            and season.champion_team_id == manager.current_team_id
        ):
            manager.championships_won += 1
        db.flush()
        return

    new_series = playoff_service.build_next_round(db, season, current_round)
    playoff_service.schedule_round_first_games(
        db, season.id, new_series, season.current_matchday
    )
    db.flush()


_ALL_LINEUP_SLOT_NAMES: tuple[str, ...] = (
    *(c for trio in LINE_FWD_SLOTS for c in trio),
    *(c for pair in PAIR_DEF_SLOTS for c in pair),
    "starting_goalie_id",
    "backup_goalie_id",
)


def _user_lineup_empty_slots(db: Session) -> list[str]:
    """Return the names of any unfilled slots in the user team's lineup, or an
    empty list if the lineup is complete (or no user team is set)."""
    user_team_id = manager_profile_service.current_team_id(db)
    if user_team_id is None:
        return []
    lu = db.query(Lineup).filter_by(team_id=user_team_id).first()
    if lu is None:
        return []
    return [name for name in _ALL_LINEUP_SLOT_NAMES if getattr(lu, name) is None]


def advance_matchday(db: Session) -> dict:
    season = db.query(Season).order_by(Season.id.desc()).first()
    if not season:
        raise LeagueNotFound("no active league")
    if season.status == "complete":
        raise SeasonAlreadyComplete("season already complete")
    if season.phase == "offseason":
        raise SeasonAlreadyComplete("season is in offseason; start the next season to continue")

    empty = _user_lineup_empty_slots(db)
    if empty:
        raise LineupIncomplete(
            f"{len(empty)} lineup slot(s) empty: {', '.join(empty)}. "
            "Fill them before simulating."
        )

    games = (
        db.query(Game)
        .filter_by(
            season_id=season.id,
            matchday=season.current_matchday,
            status="scheduled",
        )
        .order_by(Game.id)
        .all()
    )
    standings = {
        s.team_id: s for s in db.query(Standing).filter_by(season_id=season.id).all()
    }
    manager = manager_profile_service.get_active_profile(db)
    advanced_ids: list[int] = []
    affected_series_ids: set[int] = set()

    for g in games:
        gid = _simulate_game_row(db, g, season, standings, manager=manager)
        advanced_ids.append(gid)
        if g.phase == "playoffs" and g.series_id is not None:
            affected_series_ids.add(g.series_id)

    season.current_matchday += 1
    db.flush()

    if season.phase == "regular_season":
        remaining_rs = (
            db.query(Game)
            .filter_by(
                season_id=season.id, status="scheduled", phase="regular_season"
            )
            .count()
        )
        if remaining_rs == 0:
            season.phase = "playoffs"
            r1 = playoff_service.create_first_round(db, season)
            playoff_service.schedule_round_first_games(
                db, season.id, r1, season.current_matchday
            )
            db.flush()
    elif season.phase == "playoffs":
        _advance_playoffs(db, season, affected_series_ids)

    return {
        "advanced_game_ids": advanced_ids,
        "current_matchday": season.current_matchday,
        "season_status": season.status,
        "season_phase": season.phase,
    }
