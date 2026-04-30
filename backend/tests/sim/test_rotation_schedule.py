from sim.rotation import build_rotation_schedule


def test_counts_match_distribution_for_clean_split():
    sched = build_rotation_schedule(180, (0.40, 0.30, 0.20, 0.10))
    counts = [sched.count(i) for i in range(4)]
    assert counts == [72, 54, 36, 18]
    assert len(sched) == 180


def test_counts_sum_when_distribution_doesnt_round_clean():
    sched = build_rotation_schedule(15, (0.30, 0.27, 0.23, 0.20))
    assert len(sched) == 15
    counts = [sched.count(i) for i in range(4)]
    assert sum(counts) == 15
    assert all(c >= 1 for c in counts)


def test_no_long_clustering():
    sched = build_rotation_schedule(180, (0.40, 0.30, 0.20, 0.10))
    run = 1
    max_run = 1
    for a, b in zip(sched, sched[1:]):
        if a == b:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    assert max_run <= 4


def test_deterministic_across_calls():
    a = build_rotation_schedule(180, (0.40, 0.30, 0.20, 0.10))
    b = build_rotation_schedule(180, (0.40, 0.30, 0.20, 0.10))
    assert a == b


def test_returns_tuple():
    sched = build_rotation_schedule(60, (0.45, 0.35, 0.20))
    assert isinstance(sched, tuple)
    assert all(isinstance(i, int) for i in sched)
