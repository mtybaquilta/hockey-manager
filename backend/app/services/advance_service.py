from sqlalchemy.orm import Session

from app.errors import LeagueNotFound, SeasonAlreadyComplete
from app.models import (
    Game,
    GameEvent,
    Goalie,
    GoalieGameStat,
    Lineup,
    Season,
    Skater,
    SkaterGameStat,
    Standing,
)
from sim.engine import simulate_game
from sim.models import (
    Position,
    ResultType,
    SimGameInput,
    SimGoalie,
    SimLine,
    SimSkater,
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


def _build_lineup(db: Session, team_id: int) -> SimTeamLineup:
    lu = db.query(Lineup).filter_by(team_id=team_id).one()
    skater_ids = [getattr(lu, c) for trio in LINE_FWD_SLOTS for c in trio] + [
        getattr(lu, c) for pair in PAIR_DEF_SLOTS for c in pair
    ]
    skaters = {s.id: s for s in db.query(Skater).filter(Skater.id.in_(skater_ids)).all()}
    fwd_lines = tuple(
        SimLine(skaters=tuple(_to_sim_skater(skaters[getattr(lu, c)]) for c in trio))
        for trio in LINE_FWD_SLOTS
    )
    pairs = tuple(
        SimLine(skaters=tuple(_to_sim_skater(skaters[getattr(lu, c)]) for c in pair))
        for pair in PAIR_DEF_SLOTS
    )
    starter = db.query(Goalie).filter_by(id=lu.starting_goalie_id).one()
    return SimTeamLineup(
        forward_lines=fwd_lines,
        defense_pairs=pairs,
        starting_goalie=_to_sim_goalie(starter),
    )


def _apply_standing(
    stand_by_team: dict[int, Standing],
    home_id: int,
    away_id: int,
    home: int,
    away: int,
    result_type: ResultType,
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


def advance_matchday(db: Session) -> dict:
    season = db.query(Season).first()
    if not season:
        raise LeagueNotFound("no active league")
    if season.status == "complete":
        raise SeasonAlreadyComplete("season already complete")

    games = (
        db.query(Game)
        .filter_by(season_id=season.id, matchday=season.current_matchday, status="scheduled")
        .order_by(Game.id)
        .all()
    )
    standings = {s.team_id: s for s in db.query(Standing).filter_by(season_id=season.id).all()}
    advanced_ids: list[int] = []

    for g in games:
        home_lu = _build_lineup(db, g.home_team_id)
        away_lu = _build_lineup(db, g.away_team_id)
        seed = derive_game_seed(season.seed, g.id)
        result = simulate_game(SimGameInput(home=home_lu, away=away_lu, seed=seed))

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
                    kind=e.kind.value,
                    team_id=g.home_team_id if e.team_is_home else g.away_team_id,
                    primary_skater_id=e.primary_skater_id,
                    assist1_id=e.assist1_id,
                    assist2_id=e.assist2_id,
                    goalie_id=e.goalie_id,
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
        _apply_standing(
            standings, g.home_team_id, g.away_team_id, result.home_score, result.away_score, result.result_type
        )
        advanced_ids.append(g.id)

    season.current_matchday += 1
    db.flush()
    remaining = db.query(Game).filter_by(season_id=season.id, status="scheduled").count()
    if remaining == 0:
        season.status = "complete"
        db.flush()

    return {
        "advanced_game_ids": advanced_ids,
        "current_matchday": season.current_matchday,
        "season_status": season.status,
    }
