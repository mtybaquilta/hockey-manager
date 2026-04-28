import hashlib

from sim.models import SimGoalie, SimLine

GOALIE_FORM_MAX = 8.0  # max additive swing on save rating, before mental dampening


def goalie_form_offset(goalie: SimGoalie, game_seed: int) -> float:
    """Deterministic per-(goalie, game) form. Positive = sharper, negative = off.

    Amplitude shrinks with mental: a 100-mental goalie has zero variance,
    a 0-mental goalie has full GOALIE_FORM_MAX swing in either direction.
    """
    h = hashlib.sha256(f"{game_seed}:{goalie.id}".encode()).digest()
    # take 4 bytes -> uniform in [-1, 1]
    raw = int.from_bytes(h[:4], "big") / 0xFFFFFFFF
    centered = raw * 2.0 - 1.0
    dampening = max(0.0, 1.0 - goalie.mental / 100.0)
    return centered * GOALIE_FORM_MAX * dampening


def line_offense(line: SimLine) -> float:
    return sum(0.5 * s.shooting + 0.3 * s.passing + 0.2 * s.skating for s in line.skaters) / len(line.skaters)


def line_defense(line: SimLine) -> float:
    return sum(s.defense for s in line.skaters) / len(line.skaters)


def pair_defense(pair: SimLine) -> float:
    return sum(s.defense for s in pair.skaters) / len(pair.skaters)


def goalie_save_rating(g: SimGoalie) -> float:
    return 0.45 * g.reflexes + 0.35 * g.positioning + 0.1 * g.rebound_control + 0.1 * g.mental
