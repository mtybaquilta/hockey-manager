"""Sim balancing report.

Runs N deterministic games against a pair of synthetic teams and prints a
distribution summary covering shots, goals, special teams, shot quality, and
result types. Use this before/after tuning constants in `sim.engine` to see
how league averages move.

Run from the `backend/` directory:

    python -m sim.tools.run_balance_sample --games 2000

For NHL reference, target ranges:
- shots/game (per team) ~30, total ~60
- goals/game (total) ~6.0
- penalties/game ~3.0
- PP conversion ~20%
- SV% ~0.905
"""
from __future__ import annotations

import argparse
import statistics
from collections import Counter
from dataclasses import dataclass

import random

from sim.engine import simulate_game
from sim.models import EventKind, ResultType, ShotQuality, SimGameInput, Strength
from sim.tools._synthetic_team import procedural_team


@dataclass
class GameSample:
    home_shots: int
    away_shots: int
    home_goals: int
    away_goals: int
    penalties: int
    pp_goals: int
    sh_goals: int
    quality_overall: Counter
    quality_by_strength: dict[Strength, Counter]
    result_type: ResultType


def _measure(games: int, base_seed: int, team_count: int) -> list[GameSample]:
    # Build N teams once, drawn from the same distribution the real procedural
    # generator uses, then rotate matchups so we sample inter-team variance.
    team_rng = random.Random(base_seed)
    teams = [procedural_team(team_rng, id_base=1000 + 1000 * i) for i in range(team_count)]
    pair_rng = random.Random(base_seed ^ 0xA5A5A5A5)

    samples: list[GameSample] = []
    for i in range(games):
        if team_count >= 2:
            home, away = pair_rng.sample(teams, 2)
        else:
            home = away = teams[0]
        r = simulate_game(SimGameInput(home=home, away=away, seed=base_seed + i))
        quality_overall: Counter = Counter()
        quality_by_strength: dict[Strength, Counter] = {s: Counter() for s in Strength}
        penalties = pp_goals = sh_goals = 0
        for e in r.events:
            if e.kind in (EventKind.SAVE, EventKind.GOAL) and e.shot_quality is not None:
                quality_overall[e.shot_quality] += 1
                if e.strength is not None:
                    quality_by_strength[e.strength][e.shot_quality] += 1
            if e.kind == EventKind.PENALTY:
                penalties += 1
            if e.kind == EventKind.GOAL and e.strength == Strength.PP:
                pp_goals += 1
            if e.kind == EventKind.GOAL and e.strength == Strength.SH:
                sh_goals += 1
        samples.append(
            GameSample(
                home_shots=r.home_shots,
                away_shots=r.away_shots,
                home_goals=r.home_score,
                away_goals=r.away_score,
                penalties=penalties,
                pp_goals=pp_goals,
                sh_goals=sh_goals,
                quality_overall=quality_overall,
                quality_by_strength=quality_by_strength,
                result_type=r.result_type,
            )
        )
    return samples


def _fmt_pct_row(label: str, c: Counter) -> str:
    total = sum(c.values()) or 1
    parts = " ".join(f"{q.value} {c[q] / total:6.1%}" for q in ShotQuality)
    return f"  {label:<10} ({total:>6} shots)   {parts}"


def _print_report(samples: list[GameSample]) -> None:
    n = len(samples)
    total_shots = [s.home_shots + s.away_shots for s in samples]
    total_goals = [s.home_goals + s.away_goals for s in samples]
    home_shots = [s.home_shots for s in samples]
    away_shots = [s.away_shots for s in samples]
    home_goals = [s.home_goals for s in samples]
    away_goals = [s.away_goals for s in samples]
    penalties = [s.penalties for s in samples]
    pp_goals = [s.pp_goals for s in samples]
    sh_goals = [s.sh_goals for s in samples]

    sum_shots = sum(total_shots)
    sum_goals = sum(total_goals)
    league_svp = (sum_shots - sum_goals) / sum_shots if sum_shots else 0.0
    league_shp = sum_goals / sum_shots if sum_shots else 0.0

    home_wins = sum(1 for s in samples if s.home_goals > s.away_goals)
    res_counter = Counter(s.result_type for s in samples)

    pen_total = sum(penalties)
    pp_conv = sum(pp_goals) / pen_total if pen_total else 0.0

    overall_q: Counter = Counter()
    by_strength_q: dict[Strength, Counter] = {s: Counter() for s in Strength}
    for s in samples:
        overall_q.update(s.quality_overall)
        for k, v in s.quality_by_strength.items():
            by_strength_q[k].update(v)

    def fmt(values: list[float]) -> str:
        if not values:
            return "—"
        return (
            f"mean={statistics.mean(values):6.2f}  "
            f"sd={statistics.pstdev(values):5.2f}  "
            f"min={min(values):>3}  max={max(values):>3}"
        )

    print(f"\n=== Sim balance report — {n} games ===\n")
    print("Per-game totals")
    print(f"  shots (total)    {fmt(total_shots)}")
    print(f"  goals (total)    {fmt(total_goals)}")
    print(f"  penalties        {fmt(penalties)}")
    print(f"  PP goals         {fmt(pp_goals)}")
    print(f"  SH goals         {fmt(sh_goals)}")

    print("\nHome / Away splits")
    print(f"  home shots       {fmt(home_shots)}")
    print(f"  away shots       {fmt(away_shots)}")
    print(f"  home goals       {fmt(home_goals)}")
    print(f"  away goals       {fmt(away_goals)}")

    print("\nLeague rates")
    print(f"  league SV%       {league_svp:.4f}")
    print(f"  league SH%       {league_shp:.4f}")
    print(f"  home win%        {home_wins / n:.2%}")
    print(f"  OT%              {res_counter[ResultType.OT] / n:.2%}")
    print(f"  SO%              {res_counter[ResultType.SO] / n:.2%}")
    print(f"  PP conversion    {pp_conv:.2%}  ({sum(pp_goals)} PP goals on {pen_total} penalties)")

    print("\nShot quality distribution")
    print(_fmt_pct_row("overall", overall_q))
    for strength in Strength:
        print(_fmt_pct_row(strength.value, by_strength_q[strength]))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a sim balance report over N games.")
    parser.add_argument("--games", type=int, default=2000, help="Number of games to simulate")
    parser.add_argument("--seed", type=int, default=0, help="Base seed; per-game seeds are seed..seed+games-1")
    parser.add_argument(
        "--teams",
        type=int,
        default=30,
        help="Number of procedural teams to generate; matchups rotate randomly",
    )
    args = parser.parse_args()

    samples = _measure(args.games, args.seed, args.teams)
    _print_report(samples)


if __name__ == "__main__":
    main()
