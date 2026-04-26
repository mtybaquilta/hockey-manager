import hashlib


def derive_game_seed(season_seed: int, game_id: int) -> int:
    digest = hashlib.sha256(f"{season_seed}:{game_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big")
