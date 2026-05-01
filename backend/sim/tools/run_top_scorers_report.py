"""Top-20 scorers diagnostic report.

Mirrors what a real simmed season looks like: 30 teams, one fixed
"user team" (balanced/balanced) and 29 random AI gameplans, full
82-game schedule. Then prints the league's top 20 scorers with the
context needed to diagnose concentration:

- team / line / gameplan style + line_usage
- OVR + key attributes (skating / shooting / passing)
- shots, SH%
- their team's GF/G
- their team's top-line point share
- their team's top-3 teammates point share (excluding the scorer)
- their points per team goal
- their team's average assists per goal

Plus league-wide assist-per-goal so we can see if assists are inflated.

Run from `backend/`:

    python -m sim.tools.run_top_scorers_report --seed 0
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
)
from sim.tools._synthetic_team import procedural_team

STYLES = ("balanced", "offensive", "defensive", "physical")
LINE_USAGES = ("balanced", "ride_top_lines", "roll_all_lines")


@dataclass
class TeamData:
    abbr: str
    lineup: SimTeamLineup
    gameplan: SimGameplan
    gp: int = 0
    gf: int = 0
    ga: int = 0
    sf: int = 0
    sa: int = 0
    total_assists: int = 0  # primary + secondary assists awarded
    fwd_pts_by_line: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    skater_points: Counter = field(default_factory=Counter)
    skater_goals: Counter = field(default_factory=Counter)
    skater_assists: Counter = field(default_factory=Counter)
    skater_shots: Counter = field(default_factory=Counter)


def _abbr_for(i: int) -> str:
    # Friendly 3-letter abbreviations T00..T99 then AAA-style fallback.
    if i < 100:
        return f"T{i:02d}"
    base = i - 100
    return chr(ord("A") + (base // 26) % 26) + chr(ord("A") + base % 26) + "X"


def _line_index(skater_id: int, lineup: SimTeamLineup) -> int | None:
    for i, line in enumerate(lineup.forward_lines):
        if any(s.id == skater_id for s in line.skaters):
            return i
    return None


def _is_defenseman(skater_id: int, lineup: SimTeamLineup) -> bool:
    for pair in lineup.defense_pairs:
        if any(s.id == skater_id for s in pair.skaters):
            return True
    return False


def _all_skaters(lineup: SimTeamLineup):
    out = []
    for line in lineup.forward_lines:
        out.extend(line.skaters)
    for pair in lineup.defense_pairs:
        out.extend(pair.skaters)
    return out


def _ovr(s) -> int:
    return round((s.skating + s.shooting + s.passing + s.defense + s.physical) / 5)


def _measure(team_count: int, games_per_team: int, base_seed: int):
    if team_count < 2:
        raise ValueError("team_count must be >= 2")
    if (team_count * games_per_team) % 2 != 0:
        raise ValueError("team_count * games_per_team must be even")

    team_rng = random.Random(base_seed)
    gp_rng = random.Random(base_seed ^ 0x5EEDED)
    pair_rng = random.Random(base_seed ^ 0xC0FFEE)

    teams: list[TeamData] = []
    for i in range(team_count):
        lineup = procedural_team(team_rng, id_base=1000 + 1000 * i)
        if i == 0:
            gp = SimGameplan(style="balanced", line_usage="balanced")
        else:
            gp = SimGameplan(
                style=gp_rng.choice(STYLES),
                line_usage=gp_rng.choice(LINE_USAGES),
            )
        teams.append(TeamData(abbr=_abbr_for(i), lineup=lineup, gameplan=gp))

    skater_team: dict[int, int] = {}
    for ti, t in enumerate(teams):
        for s in _all_skaters(t.lineup):
            skater_team[s.id] = ti

    # Fill exactly games_per_team games per team.
    slots: list[int] = []
    for i in range(team_count):
        slots.extend([i] * games_per_team)
    pair_rng.shuffle(slots)
    pairings: list[tuple[int, int]] = []
    i = 0
    while i < len(slots):
        a, b = slots[i], slots[i + 1]
        if a == b and i + 2 < len(slots):
            slots[i + 1], slots[i + 2] = slots[i + 2], slots[i + 1]
            b = slots[i + 1]
        pairings.append((a, b))
        i += 2

    for game_i, (h_idx, a_idx) in enumerate(pairings):
        if h_idx == a_idx:
            continue
        h, a = teams[h_idx], teams[a_idx]
        r = simulate_game(SimGameInput(
            home=SimTeamInput(lineup=h.lineup, gameplan=h.gameplan),
            away=SimTeamInput(lineup=a.lineup, gameplan=a.gameplan),
            seed=base_seed + game_i,
        ))
        h.gp += 1
        a.gp += 1
        h.gf += r.home_score
        a.gf += r.away_score
        h.ga += r.away_score
        a.ga += r.home_score
        h.sf += r.home_shots
        a.sf += r.away_shots
        h.sa += r.away_shots
        a.sa += r.home_shots

        # Assists per goal at the team-level: count assist events.
        for e in r.events:
            if e.kind == EventKind.GOAL:
                team = h if e.team_is_home else a
                if e.assist1_id is not None:
                    team.total_assists += 1
                if e.assist2_id is not None:
                    team.total_assists += 1

        for ss in r.skater_stats:
            owner = skater_team.get(ss.skater_id)
            if owner is None:
                continue
            t = teams[owner]
            t.skater_goals[ss.skater_id] += ss.goals
            t.skater_assists[ss.skater_id] += ss.assists
            t.skater_shots[ss.skater_id] += ss.shots
            pts = ss.goals + ss.assists
            t.skater_points[ss.skater_id] += pts
            line_idx = _line_index(ss.skater_id, t.lineup)
            if line_idx is not None:
                t.fwd_pts_by_line[line_idx] += pts

    return teams, skater_team


def _print_report(teams: list[TeamData], skater_team: dict[int, int], top_n: int) -> None:
    n_teams = len(teams)
    total_gp = sum(t.gp for t in teams)
    total_gf = sum(t.gf for t in teams)
    total_assists = sum(t.total_assists for t in teams)
    total_points = sum(sum(t.skater_points.values()) for t in teams)

    print(f"\n=== Top scorers report — {n_teams} teams, {total_gp // 2} games ===")
    print(f"  team T00 = balanced/balanced; rest = random AI gameplans\n")

    a_per_g = (total_assists / total_gf) if total_gf else 0.0
    p_per_g = (total_points / total_gf) if total_gf else 0.0
    print("League aggregates")
    print(f"  total goals       {total_gf}")
    print(f"  total assists     {total_assists}")
    print(f"  total points      {total_points}")
    print(f"  assists / goal    {a_per_g:.3f}     (expected ~1.20 from current weights; NHL real ~1.70)")
    print(f"  points / goal     {p_per_g:.3f}     (= 1 + assists/goal)")
    print(f"  goals / team-game {total_gf / total_gp:.3f}")

    # Build a flat list of (skater_id, points) across the league.
    all_points: list[tuple[int, int]] = []
    for ti, t in enumerate(teams):
        for sid, p in t.skater_points.items():
            all_points.append((sid, p))
    all_points.sort(key=lambda kv: -kv[1])

    print(f"\nTop {top_n} scorers")
    header = (
        f"  {'#':>2} {'name':<8} {'team':<4} {'gp':<3} {'pos':<3} {'L':<2} "
        f"{'style':<10} {'usage':<14} "
        f"{'OVR':>3} {'sk/sh/pa':>8} {'P':>4} {'G':>3} {'A':>3} "
        f"{'SOG':>4} {'SH%':>5} {'tGF/G':>6} {'L1%':>5} {'top3T%':>6} {'P/tG':>5} {'A/G':>5}"
    )
    print(header)

    for rank, (sid, pts) in enumerate(all_points[:top_n], start=1):
        ti = skater_team[sid]
        t = teams[ti]
        # Find skater object for attributes.
        skater = next(s for s in _all_skaters(t.lineup) if s.id == sid)
        line_idx = _line_index(sid, t.lineup)
        if line_idx is None:
            line_label = "D"
        else:
            line_label = f"L{line_idx + 1}"
        pos = skater.position.value if hasattr(skater.position, "value") else str(skater.position)
        g = t.skater_goals[sid]
        a = t.skater_assists[sid]
        sog = t.skater_shots[sid]
        sh_pct = (g / sog) if sog else 0.0
        team_gf_g = (t.gf / t.gp) if t.gp else 0.0
        fwd_total = sum(t.fwd_pts_by_line)
        l1_share = (t.fwd_pts_by_line[0] / fwd_total) if fwd_total else 0.0
        # Top-3 teammate point share (other team scorers, excluding sid).
        teammate_pts = sorted(
            (p for sid2, p in t.skater_points.items() if sid2 != sid),
            reverse=True,
        )[:3]
        team_total_pts = sum(t.skater_points.values())
        top3_tm_share = (sum(teammate_pts) / team_total_pts) if team_total_pts else 0.0
        p_per_team_goal = (pts / t.gf) if t.gf else 0.0
        team_a_per_g = (t.total_assists / t.gf) if t.gf else 0.0

        name = f"P{sid:05d}"
        attrs = f"{skater.skating}/{skater.shooting}/{skater.passing}"
        print(
            f"  {rank:>2} {name:<8} {t.abbr:<4} {t.gp:<3} {pos:<3} {line_label:<2} "
            f"{t.gameplan.style:<10} {t.gameplan.line_usage:<14} "
            f"{_ovr(skater):>3} {attrs:>8} {pts:>4} {g:>3} {a:>3} "
            f"{sog:>4} {sh_pct:>5.1%} {team_gf_g:>6.2f} "
            f"{l1_share:>5.1%} {top3_tm_share:>6.1%} {p_per_team_goal:>5.2f} {team_a_per_g:>5.2f}"
        )

    # Per-team summary for teams that produced ≥1 top-N scorer, plus an
    # explicit listing of any team with multiple top-N forwards (UME-style
    # stacking diagnostic).
    teams_with_topN: dict[int, list[int]] = defaultdict(list)
    for sid, _ in all_points[:top_n]:
        teams_with_topN[skater_team[sid]].append(sid)
    multi = {ti: sids for ti, sids in teams_with_topN.items() if len(sids) >= 2}
    if multi:
        print("\nTeams with multiple top-{n} scorers (stacking diagnostic)".format(n=top_n))
        for ti, sids in sorted(multi.items(), key=lambda kv: -len(kv[1])):
            t = teams[ti]
            top_pts = sorted(t.skater_points.values(), reverse=True)
            line1_pts = t.fwd_pts_by_line[0]
            fwd_total = sum(t.fwd_pts_by_line)
            l1_share = (line1_pts / fwd_total) if fwd_total else 0.0
            top3 = sum(top_pts[:3])
            team_total = sum(t.skater_points.values())
            top3_share = (top3 / team_total) if team_total else 0.0
            print(
                f"  {t.abbr}  style={t.gameplan.style:<10} usage={t.gameplan.line_usage:<14} "
                f"GF/G={t.gf / t.gp:.2f}  top3-share={top3_share:.1%}  "
                f"L1-share={l1_share:.1%}  topN_count={len(sids)}  "
                f"top-points={[t.skater_points[s] for s in sids]}"
            )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Top-20 scorers report.")
    parser.add_argument("--teams", type=int, default=30)
    parser.add_argument("--games-per-team", type=int, default=82)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    teams, skater_team = _measure(args.teams, args.games_per_team, args.seed)
    _print_report(teams, skater_team, args.top)


if __name__ == "__main__":
    main()
