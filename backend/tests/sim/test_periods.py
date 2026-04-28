from sim.rotation import PERIODS, REGULATION_TICKS, TICKS_PER_PERIOD, period_at_tick


def test_period_boundaries():
    assert period_at_tick(0) == 1
    assert period_at_tick(TICKS_PER_PERIOD - 1) == 1
    assert period_at_tick(TICKS_PER_PERIOD) == 2
    assert period_at_tick(2 * TICKS_PER_PERIOD - 1) == 2
    assert period_at_tick(2 * TICKS_PER_PERIOD) == 3
    assert period_at_tick(REGULATION_TICKS - 1) == 3


def test_overtime_is_period_4():
    assert period_at_tick(REGULATION_TICKS) == PERIODS + 1
    assert period_at_tick(REGULATION_TICKS + 10) == PERIODS + 1


def test_each_period_has_equal_ticks():
    counts = [0, 0, 0]
    for t in range(REGULATION_TICKS):
        counts[period_at_tick(t) - 1] += 1
    assert counts == [TICKS_PER_PERIOD] * 3
