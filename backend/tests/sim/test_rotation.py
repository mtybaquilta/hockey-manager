from sim.rotation import REGULATION_TICKS, defense_pair_at_tick, forward_line_at_tick


def test_forward_distribution():
    counts = [0, 0, 0, 0]
    for t in range(REGULATION_TICKS):
        counts[forward_line_at_tick(t)] += 1
    assert counts == [72, 54, 36, 18]


def test_defense_distribution():
    counts = [0, 0, 0]
    for t in range(REGULATION_TICKS):
        counts[defense_pair_at_tick(t)] += 1
    assert counts == [81, 63, 36]


def test_rotation_is_deterministic():
    assert [forward_line_at_tick(t) for t in range(10)] == [forward_line_at_tick(t) for t in range(10)]
