"""Player-level scoring concentration report.

Simulates a season-sized batch of games and reports:
- top-10 scoring share (how concentrated league points are at the top)
- top-line forward point share (line1 vs line2/3/4)
- player shots distribution
- player shooting percentage distribution

Use this BEFORE retuning anything that affects scoring globally — it tells
you whether the issue is concentration or environment.

Run from the `backend/` directory:

    python -m sim.tools.run_scoring_report --games 600 --teams 16
"""
from __future__ import annotations

import argparse
import random
import statistics
from collections import Counter, defaultdict

from sim.engine import simulate_game
from sim.models import SimGameInput, SimGameplan, SimTeamInput
from sim.tools._synthetic_team import procedural_team


def _wrap(lineup) -> SimTeamInput:
    return SimTeamInput(lineup=lineup, gameplan=SimGameplan(style="balanced", line_usage="balanced"))


def _line_index(skater_id: int, lineup) -> int | None:
    for i, line in enumerate(lineup.forward_lines):
        if any(s.id == skater_id for s in line.skaters):
            return i
    return None


def _measure(games: int, base_seed: int, team_count: int):
    team_rng = random.Random(base_seed)
    teams = [procedural_team(team_rng, id_base=1000 + 1000 * i) for i in range(team_count)]
    team_by_id = {team_id: t for t in teams for team_id in (id(t),)}  # placeholder
    pair_rng = random.Random(base_seed ^ 0xC0FFEE)

    points: Counter[int] = Counter()
    goals: Counter[int] = Counter()
    assists: Counter[int] = Counter()
    shots: Counter[int] = Counter()
    line_points: dict[int, int] = defaultdict(int)  # 0..3
    line_points["other"] = 0  # type: ignore[index]
    line_points_by_idx: list[int] = [0, 0, 0, 0]

    for i in range(games):
        if team_count >= 2:
            home, away = pair_rng.sample(teams, 2)
        else:
            home = away = teams[0]
        r = simulate_game(SimGameInput(home=_wrap(home), away=_wrap(away), seed=base_seed + i))
        for ss in r.skater_stats:
            shots[ss.skater_id] += ss.shots
            goals[ss.skater_id] += ss.goals
            assists[ss.skater_id] += ss.assists
            points[ss.skater_id] += ss.goals + ss.assists
            for lineup in (home, away):
                idx = _line_index(ss.skater_id, lineup)
                if idx is not None:
                    line_points_by_idx[idx] += ss.goals + ss.assists
                    break

    return points, goals, assists, shots, line_points_by_idx


def _print_report(
    points: Counter[int],
    goals: Counter[int],
    assists: Counter[int],
    shots: Counter[int],
    line_points_by_idx: list[int],
    games: int,
) -> None:
    n_skaters = len(points)
    total_points = sum(points.values())
    total_goals = sum(goals.values())
    total_shots = sum(shots.values())

    print(f"\n=== Scoring concentration report — {games} games, {n_skaters} skaters ===\n")

    # Top-N scoring share.
    sorted_pts = sorted(points.items(), key=lambda kv: -kv[1])
    for k in (5, 10, 25, 50):
        if k > len(sorted_pts):
            continue
        top_pts = sum(p for _, p in sorted_pts[:k])
        share = top_pts / total_points if total_points else 0
        print(f"  top-{k:>3} pts share   {share:6.2%}   ({top_pts}/{total_points})")

    # Top scorer slice.
    if sorted_pts:
        sid, pts = sorted_pts[0]
        g, a, sh = goals[sid], assists[sid], shots[sid]
        sh_pct = (g / sh) if sh else 0.0
        print(f"\n  top scorer        {pts} pts ({g}G {a}A) on {sh} shots, SH% {sh_pct:.1%}")

    # Forward line point share (line1..line4).
    print("\nForward line point share (forwards only)")
    fwd_total = sum(line_points_by_idx)
    if fwd_total:
        for i, p in enumerate(line_points_by_idx):
            print(f"  line {i + 1}            {p / fwd_total:6.2%}   ({p}/{fwd_total})")

    # Per-player shots distribution.
    if shots:
        sh_values = list(shots.values())
        sh_values.sort(reverse=True)
        print("\nPlayer shot totals (per player, full sample)")
        print(
            f"  mean={statistics.mean(sh_values):6.1f}  "
            f"median={statistics.median(sh_values):6.1f}  "
            f"p90={sh_values[int(len(sh_values) * 0.10)]:>4}  "
            f"max={max(sh_values)}"
        )

    # Per-player shooting % (≥30 shots only, to avoid noise).
    qualified = [(sid, goals[sid] / shots[sid]) for sid, sh in shots.items() if sh >= 30]
    if qualified:
        pcts = [p for _, p in qualified]
        pcts.sort(reverse=True)
        print(f"\nShooting % (players with ≥30 shots, n={len(qualified)})")
        print(
            f"  mean={statistics.mean(pcts):.1%}  "
            f"median={statistics.median(pcts):.1%}  "
            f"top={pcts[0]:.1%}  bottom={pcts[-1]:.1%}"
        )

    # League aggregates for context.
    league_shp = total_goals / total_shots if total_shots else 0.0
    print(f"\nLeague aggregates")
    print(f"  total points        {total_points}")
    print(f"  total goals         {total_goals}")
    print(f"  total shots         {total_shots}")
    print(f"  league SH%          {league_shp:.4f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Player-level scoring concentration report.",
    )
    parser.add_argument("--games", type=int, default=600)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--teams", type=int, default=16)
    args = parser.parse_args()

    points, goals, assists, shots, line_points_by_idx = _measure(
        args.games, args.seed, args.teams
    )
    _print_report(points, goals, assists, shots, line_points_by_idx, args.games)


if __name__ == "__main__":
    main()
