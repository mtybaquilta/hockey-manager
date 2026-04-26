from sim.seed import derive_game_seed


def test_seed_is_stable_across_calls():
    assert derive_game_seed(42, 7) == derive_game_seed(42, 7)


def test_seed_changes_with_inputs():
    assert derive_game_seed(42, 7) != derive_game_seed(42, 8)
    assert derive_game_seed(42, 7) != derive_game_seed(43, 7)


def test_seed_is_int():
    assert isinstance(derive_game_seed(123, 456), int)
