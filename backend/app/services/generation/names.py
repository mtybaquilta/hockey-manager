import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "data"


def _load(name: str):
    return json.loads((DATA / name).read_text())


def sample_team_names(rng: random.Random, n: int) -> list[dict]:
    pool = _load("team_names.json")
    rng.shuffle(pool)
    return pool[:n]


def make_player_name(rng: random.Random, used: set[str]) -> str:
    firsts = _load("first_names.json")
    lasts = _load("last_names.json")
    while True:
        name = f"{rng.choice(firsts)} {rng.choice(lasts)}"
        if name not in used:
            used.add(name)
            return name
