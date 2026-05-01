"""Player-level scoring concentration report.

Simulates a season-sized batch of games and reports:
- top-N scoring share (how concentrated league points are at the top)
- top-line forward point share (line1 vs line2/3/4)
- player shots distribution + top-5 / top-scorer team-shot share
- player shooting percentage distribution
- per-team shot totals: team-only vs opponent vs combined, cross-checked
  against game.home_shots / game.away_shots

Use this BEFORE retuning anything that affects scoring globally — it tells
you whether the issue is concentration or environment.

Run from the `backend/` directory:

    python -m sim.tools.run_scoring_report --games 656 --teams 16
"""
from __future__ import annotations

import argparse
import random
import statistics
from collections import Counter, defaultdict

from sim.engine import simulate_game
from sim.models import SimGameInput, SimGameplan, SimTeamInput, SimTeamLineup
from sim.tools._synthetic_team import procedural_team

GAMEPLAN_STYLE = "balanced"
GAMEPLAN_LINE_USAGE = "balanced"


def _wrap(lineup: SimTeamLineup) -> SimTeamInput:
    return SimTeamInput(
        lineup=lineup,
        gameplan=SimGameplan(style=GAMEPLAN_STYLE, line_usage=GAMEPLAN_LINE_USAGE),
    )


def _line_index(skater_id: int, lineup: SimTeamLineup) -> int | None:
    for i, line in enumerate(lineup.forward_lines):
        if any(s.id == skater_id for s in line.skaters):
            return i
    return None


def _team_skater_ids(lineup: SimTeamLineup) -> set[int]:
    ids: set[int] = set()
    for line in lineup.forward_lines:
        for s in line.skaters:
            ids.add(s.id)
    for pair in lineup.defense_pairs:
        for s in pair.skaters:
            ids.add(s.id)
    return ids


def _measure(games: int, base_seed: int, team_count: int):
    if team_count < 2:
        raise ValueError("team_count must be >= 2 so home/away are distinct teams")

    team_rng = random.Random(base_seed)
    teams = [procedural_team(team_rng, id_base=1000 + 1000 * i) for i in range(team_count)]
    pair_rng = random.Random(base_seed ^ 0xC0FFEE)

    points: Counter[int] = Counter()
    goals: Counter[int] = Counter()
    assists: Counter[int] = Counter()
    shots: Counter[int] = Counter()
    line_points_by_idx: list[int] = [0, 0, 0, 0]

    # skater_id -> team index, for team-shot-share lookups.
    team_of_skater: dict[int, int] = {}
    for i, team in enumerate(teams):
        for sid in _team_skater_ids(team):
            team_of_skater[sid] = i

    # Per-team accounting for cross-checks.
    team_games: list[int] = [0] * team_count
    team_skater_shots: list[int] = [0] * team_count    # sum of own players' shots
    team_skater_shots_against: list[int] = [0] * team_count  # opp players' shots
    team_engine_shots_for: list[int] = [0] * team_count   # game.home_shots/away_shots for THIS team
    team_engine_shots_against: list[int] = [0] * team_count  # game.*_shots for the OTHER team

    for i in range(games):
        home, away = pair_rng.sample(teams, 2)
        home_idx = teams.index(home)
        away_idx = teams.index(away)
        r = simulate_game(SimGameInput(home=_wrap(home), away=_wrap(away), seed=base_seed + i))

        team_games[home_idx] += 1
        team_games[away_idx] += 1
        team_engine_shots_for[home_idx] += r.home_shots
        team_engine_shots_for[away_idx] += r.away_shots
        team_engine_shots_against[home_idx] += r.away_shots
        team_engine_shots_against[away_idx] += r.home_shots

        for ss in r.skater_stats:
            shots[ss.skater_id] += ss.shots
            goals[ss.skater_id] += ss.goals
            assists[ss.skater_id] += ss.assists
            points[ss.skater_id] += ss.goals + ss.assists
            owner = team_of_skater.get(ss.skater_id)
            if owner is not None:
                team_skater_shots[owner] += ss.shots
                # opponent in this specific game:
                opp = away_idx if owner == home_idx else home_idx
                team_skater_shots_against[opp] += ss.shots
            for lineup in (home, away):
                idx = _line_index(ss.skater_id, lineup)
                if idx is not None:
                    line_points_by_idx[idx] += ss.goals + ss.assists
                    break

    return {
        "points": points,
        "goals": goals,
        "assists": assists,
        "shots": shots,
        "line_points_by_idx": line_points_by_idx,
        "teams": teams,
        "team_of_skater": team_of_skater,
        "team_games": team_games,
        "team_skater_shots": team_skater_shots,
        "team_skater_shots_against": team_skater_shots_against,
        "team_engine_shots_for": team_engine_shots_for,
        "team_engine_shots_against": team_engine_shots_against,
    }


def _print_report(data: dict, games: int) -> None:
    points: Counter[int] = data["points"]
    goals: Counter[int] = data["goals"]
    shots: Counter[int] = data["shots"]
    line_points_by_idx: list[int] = data["line_points_by_idx"]
    teams: list[SimTeamLineup] = data["teams"]
    team_of_skater: dict[int, int] = data["team_of_skater"]
    team_games: list[int] = data["team_games"]
    team_skater_shots: list[int] = data["team_skater_shots"]
    team_skater_shots_against: list[int] = data["team_skater_shots_against"]
    team_engine_shots_for: list[int] = data["team_engine_shots_for"]
    team_engine_shots_against: list[int] = data["team_engine_shots_against"]

    n_skaters = len(points)
    total_points = sum(points.values())
    total_goals = sum(goals.values())
    total_shots = sum(shots.values())

    print(f"\n=== Scoring concentration report — {games} games, {n_skaters} skaters ===")
    print(f"    gameplan: style={GAMEPLAN_STYLE}  line_usage={GAMEPLAN_LINE_USAGE}\n")

    # Top-N scoring share.
    sorted_pts = sorted(points.items(), key=lambda kv: -kv[1])
    for k in (5, 10, 25, 50):
        if k > len(sorted_pts):
            continue
        top_pts = sum(p for _, p in sorted_pts[:k])
        share = top_pts / total_points if total_points else 0
        print(f"  top-{k:>3} pts share   {share:6.2%}   ({top_pts}/{total_points})")

    # Top scorer slice with team / line / per-game context.
    if sorted_pts:
        sid, pts = sorted_pts[0]
        g, a, sh = goals[sid], int(points[sid] - goals[sid]), shots[sid]
        sh_pct = (g / sh) if sh else 0.0
        t_idx = team_of_skater.get(sid)
        line_idx = _line_index(sid, teams[t_idx]) if t_idx is not None else None
        line_label = f"L{line_idx + 1}" if line_idx is not None else "D"
        team_sh = team_skater_shots[t_idx] if t_idx is not None else 0
        gp = team_games[t_idx] if t_idx is not None else 0
        team_share = (sh / team_sh) if team_sh else 0.0
        per_game = (sh / gp) if gp else 0.0
        print(
            f"\n  top scorer        {pts} pts ({g}G {a}A) on {sh} shots, SH% {sh_pct:.1%}"
            f"  [{line_label}, team {t_idx}, GP={gp}]"
        )
        print(f"  top scorer shots per team game: {per_game:.2f}")
        print(f"  top scorer share of team-only shots: {team_share:.1%}  ({sh}/{team_sh})")

    # Forward line point share (line1..line4).
    print("\nForward line point share (forwards only)")
    fwd_total = sum(line_points_by_idx)
    if fwd_total:
        for i, p in enumerate(line_points_by_idx):
            print(f"  line {i + 1}            {p / fwd_total:6.2%}   ({p}/{fwd_total})")

    # Per-team shot totals: team-only vs opponent vs combined, with cross-check
    # against engine-reported home_shots/away_shots.
    print("\nPer-team shot totals (avg per team-game)")
    tot_team = sum(team_skater_shots)
    tot_opp = sum(team_skater_shots_against)
    tot_eng_for = sum(team_engine_shots_for)
    tot_eng_against = sum(team_engine_shots_against)
    tot_team_games = sum(team_games)
    avg_team = tot_team / tot_team_games if tot_team_games else 0.0
    avg_opp = tot_opp / tot_team_games if tot_team_games else 0.0
    avg_combined = (tot_team + tot_opp) / tot_team_games if tot_team_games else 0.0
    print(f"  team shots only       sum={tot_team:>7}  avg/g={avg_team:5.2f}")
    print(f"  opponent shots        sum={tot_opp:>7}  avg/g={avg_opp:5.2f}")
    print(f"  combined shots        sum={tot_team + tot_opp:>7}  avg/g={avg_combined:5.2f}")
    print("  cross-check vs engine game.home_shots/away_shots:")
    print(
        f"    sum(player shots, team)     = {tot_team}   "
        f"engine shots_for     = {tot_eng_for}   "
        f"diff = {tot_team - tot_eng_for}"
    )
    print(
        f"    sum(player shots, opp)      = {tot_opp}   "
        f"engine shots_against = {tot_eng_against}   "
        f"diff = {tot_opp - tot_eng_against}"
    )

    # Per-player shots distribution (full sample, league-wide).
    if shots:
        sh_values = sorted(shots.values(), reverse=True)
        print("\nPlayer shot totals (per player, full sample)")
        print(
            f"  mean={statistics.mean(sh_values):6.1f}  "
            f"median={statistics.median(sh_values):6.1f}  "
            f"p90={sh_values[int(len(sh_values) * 0.10)]:>4}  "
            f"max={max(sh_values)}"
        )
        top5 = sum(sh_values[:5])
        print(
            f"  top-5 shot share  {top5 / total_shots:6.2%}   "
            f"({top5}/{total_shots})  top5={sh_values[:5]}"
        )

    # Per-player shooting % (≥30 shots only, to avoid noise).
    qualified = [(sid, goals[sid] / shots[sid]) for sid, sh in shots.items() if sh >= 30]
    if qualified:
        pcts = sorted((p for _, p in qualified), reverse=True)
        print(f"\nShooting % (players with ≥30 shots, n={len(qualified)})")
        print(
            f"  mean={statistics.mean(pcts):.1%}  "
            f"median={statistics.median(pcts):.1%}  "
            f"top={pcts[0]:.1%}  bottom={pcts[-1]:.1%}"
        )

    league_shp = total_goals / total_shots if total_shots else 0.0
    print(f"\nLeague aggregates")
    print(f"  total points        {total_points}")
    print(f"  total goals         {total_goals}")
    print(f"  total shots (sum players)  {total_shots}")
    print(f"  total engine shots  {tot_eng_for}  (== sum of home_shots+away_shots)")
    print(f"  league SH%          {league_shp:.4f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Player-level scoring concentration report.",
    )
    parser.add_argument("--games", type=int, default=656)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--teams", type=int, default=16)
    args = parser.parse_args()

    data = _measure(args.games, args.seed, args.teams)
    _print_report(data, args.games)


if __name__ == "__main__":
    main()
