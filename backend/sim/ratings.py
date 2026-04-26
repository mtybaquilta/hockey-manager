from sim.models import SimGoalie, SimLine


def line_offense(line: SimLine) -> float:
    return sum(0.5 * s.shooting + 0.3 * s.passing + 0.2 * s.skating for s in line.skaters) / len(line.skaters)


def line_defense(line: SimLine) -> float:
    return sum(s.defense for s in line.skaters) / len(line.skaters)


def pair_defense(pair: SimLine) -> float:
    return sum(s.defense for s in pair.skaters) / len(pair.skaters)


def goalie_save_rating(g: SimGoalie) -> float:
    return 0.45 * g.reflexes + 0.35 * g.positioning + 0.1 * g.rebound_control + 0.1 * g.mental
