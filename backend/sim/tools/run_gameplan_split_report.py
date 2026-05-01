"""Mixed-gameplan league report.

Simulates a full 30-team season with AI-generated gameplans (one fixed
balanced "user team" + 29 random AI gameplans) and prints per-style and
per-line_usage splits, plus league averages, so we can verify the
gameplan modifiers move the right dials without breaking league averages.

Run from the `backend/` directory:

    python -m sim.tools.run_gameplan_split_report --seed 0
"""
from __future__ import annotations

import argparse
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from sim.engine import simulate_game
from sim.models import (
    EventKind,
    SimGameInput,
    SimGameplan,
    SimTeamInput,
    SimTeamLineup,
    Strength,
)
from sim.tools._synthetic_team import procedural_team

STYLES = ("balanced", "offensive", "defensive", "physical")
LINE_USAGES = ("balanced", "ride_top_lines", "roll_all_lines")


@dataclass
class TeamAgg:
    gp: int = 0
    gf: int = 0
    ga: int = 0
    sf: int = 0
    sa: int = 0
    penalties_committed: int = 0  # minor penalties drawn against this team
    pp_opps_for: int = 0          # opp penalties committed (= our PP chances)
    pp_goals_for: int = 0
    pp_goals_against: int = 0
    top6_pts: int = 0   # line1 + line2 forwards points
    bot6_pts: int = 0   # line3 + line4 forwards points
    fwd_pts_total: int = 0


def _team_skater_ids(lineup: SimTeamLineup) -> set[int]:
    out: set[int] = set()
    for line in lineup.forward_lines:
        for s in line.skaters:
            out.add(s.id)
    for pair in lineup.defense_pairs:
        for s in pair.skaters:
            out.add(s.id)
    return out


def _line_index(skater_id: int, lineup: SimTeamLineup) -> int | None:
    for i, line in enumerate(lineup.forward_lines):
        if any(s.id == skater_id for s in line.skaters):
            return i
    return None


def _random_gameplan(rng: random.Random) -> SimGameplan:
    return SimGameplan(style=rng.choice(STYLES), line_usage=rng.choice(LINE_USAGES))


def _measure(team_count: int, games_per_team: int, base_seed: int):
    if team_count < 2:
        raise ValueError("team_count must be >= 2")
    if team_count * games_per_team % 2 != 0:
        raise ValueError("team_count * games_per_team must be even")

    team_rng = random.Random(base_seed)
    gp_rng = random.Random(base_seed ^ 0x5EEDED)
    pair_rng = random.Random(base_seed ^ 0xC0FFEE)

    teams = [procedural_team(team_rng, id_base=1000 + 1000 * i) for i in range(team_count)]
    # Team 0 = user team, fixed balanced/balanced. Rest = random AI gameplans.
    gameplans: list[SimGameplan] = [SimGameplan(style="balanced", line_usage="balanced")]
    for _ in range(team_count - 1):
        gameplans.append(_random_gameplan(gp_rng))

    skater_team: dict[int, int] = {}
    for i, team in enumerate(teams):
        for sid in _team_skater_ids(team):
            skater_team[sid] = i

    aggs = [TeamAgg() for _ in range(team_count)]

    # Random pairings to fill exactly games_per_team games per team.
    # Use a slot-based scheduler: each team gets `games_per_team` slots, then
    # pair slots randomly while avoiding self-pair when possible.
    slots: list[int] = []
    for i in range(team_count):
        slots.extend([i] * games_per_team)
    pair_rng.shuffle(slots)
    pairings: list[tuple[int, int]] = []
    i = 0
    while i < len(slots):
        a = slots[i]
        b = slots[i + 1]
        if a == b and i + 2 < len(slots):
            slots[i + 1], slots[i + 2] = slots[i + 2], slots[i + 1]
            b = slots[i + 1]
        pairings.append((a, b))
        i += 2

    for game_i, (h_idx, a_idx) in enumerate(pairings):
        if h_idx == a_idx:
            continue
        home = SimTeamInput(lineup=teams[h_idx], gameplan=gameplans[h_idx])
        away = SimTeamInput(lineup=teams[a_idx], gameplan=gameplans[a_idx])
        r = simulate_game(SimGameInput(home=home, away=away, seed=base_seed + game_i))

        ah = aggs[h_idx]
        aa = aggs[a_idx]
        ah.gp += 1
        aa.gp += 1
        ah.gf += r.home_score
        aa.gf += r.away_score
        ah.ga += r.away_score
        aa.ga += r.home_score
        ah.sf += r.home_shots
        aa.sf += r.away_shots
        ah.sa += r.away_shots
        aa.sa += r.home_shots

        # Penalty + PP accounting from events.
        for e in r.events:
            if e.kind == EventKind.PENALTY:
                if e.team_is_home:
                    ah.penalties_committed += 1
                    aa.pp_opps_for += 1
                else:
                    aa.penalties_committed += 1
                    ah.pp_opps_for += 1
            elif e.kind == EventKind.GOAL and e.strength == Strength.PP:
                if e.team_is_home:
                    ah.pp_goals_for += 1
                    aa.pp_goals_against += 1
                else:
                    aa.pp_goals_for += 1
                    ah.pp_goals_against += 1

        # Forward top-six / bottom-six point share.
        for ss in r.skater_stats:
            owner = skater_team.get(ss.skater_id)
            if owner is None:
                continue
            line_idx = _line_index(ss.skater_id, teams[owner])
            if line_idx is None:
                continue  # defenseman
            pts = ss.goals + ss.assists
            aggs[owner].fwd_pts_total += pts
            if line_idx <= 1:
                aggs[owner].top6_pts += pts
            else:
                aggs[owner].bot6_pts += pts

    return teams, gameplans, aggs


def _avg(num: int, denom: int) -> float:
    return (num / denom) if denom else 0.0


def _per_game(values: list[float], gps: list[int]) -> float:
    """Weighted-by-games average."""
    n = sum(gps)
    if not n:
        return 0.0
    return sum(v * g for v, g in zip(values, gps)) / n


def _split_block(
    title: str,
    keys: tuple[str, ...],
    group_of: list[str],
    aggs: list[TeamAgg],
    metrics: list[tuple[str, callable]],
) -> None:
    print(f"\n{title}")
    header = f"  {'group':<16} " + " ".join(f"{m[0]:>9}" for m in metrics) + "   teams  GP"
    print(header)
    for k in keys:
        idxs = [i for i, g in enumerate(group_of) if g == k]
        if not idxs:
            continue
        gps = [aggs[i].gp for i in idxs]
        row_vals = []
        for _, fn in metrics:
            per_team_vals = [fn(aggs[i]) for i in idxs]
            row_vals.append(_per_game(per_team_vals, gps))
        cells = " ".join(f"{v:9.3f}" for v in row_vals)
        print(f"  {k:<16} {cells}   {len(idxs):>5}  {sum(gps):>4}")


def _print_report(
    teams: list[SimTeamLineup],
    gameplans: list[SimGameplan],
    aggs: list[TeamAgg],
) -> None:
    n_teams = len(teams)
    total_gp = sum(a.gp for a in aggs)
    total_gf = sum(a.gf for a in aggs)
    total_sf = sum(a.sf for a in aggs)
    total_pen = sum(a.penalties_committed for a in aggs)
    total_pp_for = sum(a.pp_opps_for for a in aggs)
    total_pp_g = sum(a.pp_goals_for for a in aggs)

    # Each game contributes 2 to total_gp; "team-games" == total_gp.
    print(f"\n=== Mixed-gameplan league report — {n_teams} teams, {total_gp // 2} games ===")
    print(f"  team 0 = user team (balanced/balanced); teams 1..{n_teams - 1} = random AI gameplans\n")

    # Gameplan distribution.
    style_counts = Counter(gp.style for gp in gameplans)
    line_counts = Counter(gp.line_usage for gp in gameplans)
    print("Gameplan distribution")
    print(f"  style:       {dict(style_counts)}")
    print(f"  line_usage:  {dict(line_counts)}")

    # League aggregates.
    league_goals_per_g = total_gf / (total_gp / 2) if total_gp else 0.0
    league_shots_per_team_g = total_sf / total_gp if total_gp else 0.0
    league_shp = total_gf / total_sf if total_sf else 0.0
    league_pen_per_team_g = total_pen / total_gp if total_gp else 0.0
    league_pp_pct = (total_pp_g / total_pp_for) if total_pp_for else 0.0
    print("\nLeague aggregates")
    print(f"  goals / game (combined):   {league_goals_per_g:.3f}")
    print(f"  shots / team-game:         {league_shots_per_team_g:.3f}")
    print(f"  league SH%:                {league_shp:.4f}")
    print(f"  penalties / team-game:     {league_pen_per_team_g:.3f}")
    print(f"  league PP%:                {league_pp_pct:.3f}  ({total_pp_g}/{total_pp_for})")

    # Style splits.
    style_of = [gp.style for gp in gameplans]
    style_metrics: list[tuple[str, callable]] = [
        ("GF/G", lambda a: _avg(a.gf, a.gp)),
        ("GA/G", lambda a: _avg(a.ga, a.gp)),
        ("SF/G", lambda a: _avg(a.sf, a.gp)),
        ("SA/G", lambda a: _avg(a.sa, a.gp)),
        ("PEN/G", lambda a: _avg(a.penalties_committed, a.gp)),
        ("PPA/G", lambda a: _avg(a.pp_goals_against, a.gp)),
    ]
    _split_block("By style", STYLES, style_of, aggs, style_metrics)

    # Line-usage splits — focus on top6 vs bot6 forward point share.
    lu_of = [gp.line_usage for gp in gameplans]
    lu_metrics: list[tuple[str, callable]] = [
        ("GF/G", lambda a: _avg(a.gf, a.gp)),
        ("SF/G", lambda a: _avg(a.sf, a.gp)),
        ("top6%", lambda a: _avg(a.top6_pts, a.fwd_pts_total)),
        ("bot6%", lambda a: _avg(a.bot6_pts, a.fwd_pts_total)),
    ]
    _split_block("By line_usage", LINE_USAGES, lu_of, aggs, lu_metrics)

    # User team callout.
    u = aggs[0]
    print("\nUser team (team 0, balanced/balanced)")
    print(
        f"  GP={u.gp}  GF/G={_avg(u.gf, u.gp):.2f}  GA/G={_avg(u.ga, u.gp):.2f}  "
        f"SF/G={_avg(u.sf, u.gp):.2f}  SA/G={_avg(u.sa, u.gp):.2f}  "
        f"PEN/G={_avg(u.penalties_committed, u.gp):.2f}  "
        f"top6%={_avg(u.top6_pts, u.fwd_pts_total):.1%}"
    )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Mixed-gameplan league report.")
    parser.add_argument("--teams", type=int, default=30)
    parser.add_argument("--games-per-team", type=int, default=82)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    teams, gameplans, aggs = _measure(args.teams, args.games_per_team, args.seed)
    _print_report(teams, gameplans, aggs)


if __name__ == "__main__":
    main()
