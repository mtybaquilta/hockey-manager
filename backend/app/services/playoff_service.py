from sqlalchemy.orm import Session

from app.models import Game, PlayoffSeries, Season, Standing

# Round 1 pairings by overall seed. Order matters: bracket_slot is the index
# into this list, and round-2 pairs slots [0,1], [2,3], [4,5], [6,7].
R1_PAIRINGS: list[tuple[int, int]] = [
    (1, 16),
    (8, 9),
    (4, 13),
    (5, 12),
    (2, 15),
    (7, 10),
    (3, 14),
    (6, 11),
]
GAMES_TO_WIN = 4
# Game numbers (1-indexed) where the higher seed has home ice in a 2-2-1-1-1 format.
HIGH_SEED_HOME_GAMES: frozenset[int] = frozenset({1, 2, 5, 7})
PLAYOFF_TEAM_COUNT = 16
ROUND_FINAL = 4


def _seeded_team_ids(db: Session, season_id: int) -> list[int]:
    """Top 16 team_ids sorted by points/diff/team_id (matches /standings ordering)."""
    rows = db.query(Standing).filter_by(season_id=season_id).all()
    rows.sort(key=lambda s: (-s.points, -(s.goals_for - s.goals_against), s.team_id))
    return [r.team_id for r in rows[:PLAYOFF_TEAM_COUNT]]


def create_first_round(db: Session, season: Season) -> list[PlayoffSeries]:
    seeds = _seeded_team_ids(db, season.id)
    if len(seeds) < PLAYOFF_TEAM_COUNT:
        raise ValueError(
            f"need {PLAYOFF_TEAM_COUNT} seeded teams, got {len(seeds)}"
        )
    series_list: list[PlayoffSeries] = []
    for slot, (h_seed, l_seed) in enumerate(R1_PAIRINGS):
        s = PlayoffSeries(
            season_id=season.id,
            round=1,
            bracket_slot=slot,
            high_seed=h_seed,
            low_seed=l_seed,
            high_seed_team_id=seeds[h_seed - 1],
            low_seed_team_id=seeds[l_seed - 1],
            wins_high=0,
            wins_low=0,
            status="active",
        )
        db.add(s)
        series_list.append(s)
    db.flush()
    return series_list


def schedule_next_game_for_series(
    db: Session, series: PlayoffSeries, season_id: int, matchday: int
) -> Game:
    game_num = series.wins_high + series.wins_low + 1
    high_home = game_num in HIGH_SEED_HOME_GAMES
    home = series.high_seed_team_id if high_home else series.low_seed_team_id
    away = series.low_seed_team_id if high_home else series.high_seed_team_id
    g = Game(
        season_id=season_id,
        matchday=matchday,
        home_team_id=home,
        away_team_id=away,
        status="scheduled",
        phase="playoffs",
        series_id=series.id,
        game_in_series=game_num,
    )
    db.add(g)
    db.flush()
    return g


def schedule_round_first_games(
    db: Session,
    season_id: int,
    series_list: list[PlayoffSeries],
    matchday: int,
) -> None:
    for s in series_list:
        if s.status == "active":
            schedule_next_game_for_series(db, s, season_id, matchday)


def recompute_series_state(db: Session, series: PlayoffSeries) -> None:
    """Recount wins from simulated games and mark complete if 4 reached."""
    games = (
        db.query(Game)
        .filter_by(series_id=series.id, status="simulated")
        .all()
    )
    wins_high = 0
    wins_low = 0
    for g in games:
        home_won = (g.home_score or 0) > (g.away_score or 0)
        high_is_home = g.home_team_id == series.high_seed_team_id
        high_won = home_won == high_is_home
        if high_won:
            wins_high += 1
        else:
            wins_low += 1
    series.wins_high = wins_high
    series.wins_low = wins_low
    if wins_high >= GAMES_TO_WIN:
        series.winner_team_id = series.high_seed_team_id
        series.status = "complete"
    elif wins_low >= GAMES_TO_WIN:
        series.winner_team_id = series.low_seed_team_id
        series.status = "complete"


def _winner_seed(series: PlayoffSeries) -> int:
    return (
        series.high_seed
        if series.winner_team_id == series.high_seed_team_id
        else series.low_seed
    )


def build_next_round(
    db: Session, season: Season, completed_round: int
) -> list[PlayoffSeries]:
    """Pair winners from completed_round into the next round. The winner with
    the better (lower-numbered) original seed becomes the higher seed of the
    new series and keeps home ice."""
    prev = (
        db.query(PlayoffSeries)
        .filter_by(season_id=season.id, round=completed_round)
        .order_by(PlayoffSeries.bracket_slot)
        .all()
    )
    new_round = completed_round + 1
    new_series: list[PlayoffSeries] = []
    for slot in range(len(prev) // 2):
        a = prev[2 * slot]
        b = prev[2 * slot + 1]
        a_seed = _winner_seed(a)
        b_seed = _winner_seed(b)
        if a_seed <= b_seed:
            high_team, high_seed, low_team, low_seed = (
                a.winner_team_id, a_seed, b.winner_team_id, b_seed,
            )
        else:
            high_team, high_seed, low_team, low_seed = (
                b.winner_team_id, b_seed, a.winner_team_id, a_seed,
            )
        s = PlayoffSeries(
            season_id=season.id,
            round=new_round,
            bracket_slot=slot,
            high_seed=high_seed,
            low_seed=low_seed,
            high_seed_team_id=high_team,
            low_seed_team_id=low_team,
            wins_high=0,
            wins_low=0,
            status="active",
        )
        db.add(s)
        new_series.append(s)
    db.flush()
    return new_series


def latest_round(db: Session, season_id: int) -> int | None:
    """Highest round currently created for the season. None before R1 is built."""
    series = (
        db.query(PlayoffSeries)
        .filter_by(season_id=season_id)
        .order_by(PlayoffSeries.round.desc())
        .first()
    )
    return series.round if series else None
