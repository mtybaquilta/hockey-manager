import statistics

from sim.development import (
    DevEvent,
    GOALIE_ATTRIBUTES,
    PlayerDevInput,
    SKATER_ATTRIBUTES,
    classify_summary,
    develop_player,
    overall_from_attrs,
)


def _skater_input(**overrides) -> PlayerDevInput:
    base = dict(
        player_id=1,
        player_type="skater",
        age=24,
        attrs={"skating": 75, "shooting": 75, "passing": 75, "defense": 75, "physical": 75},
        potential=85,
        development_type="steady",
        perf_signal=0.0,
    )
    base.update(overrides)
    return PlayerDevInput(**base)


def test_overall_skater_is_attribute_average():
    p = _skater_input()
    assert overall_from_attrs(p) == 75


def test_skater_attribute_set():
    assert SKATER_ATTRIBUTES == ("skating", "shooting", "passing", "defense", "physical")


def test_goalie_attribute_set():
    assert GOALIE_ATTRIBUTES == (
        "reflexes",
        "positioning",
        "rebound_control",
        "puck_handling",
        "mental",
    )


def _cohort(make_input, n=400, seed=12345):
    return [develop_player(make_input(i), season_seed=seed) for i in range(n)]


def test_determinism():
    p = _skater_input(player_id=42)
    a = develop_player(p, season_seed=99)
    b = develop_player(p, season_seed=99)
    assert a == b


def test_young_high_potential_grows_on_average():
    def make(i: int):
        return _skater_input(
            player_id=i,
            age=19,
            attrs={k: 70 for k in SKATER_ATTRIBUTES},
            potential=90,
        )
    results = _cohort(make)
    deltas = [r.overall_after - r.overall_before for r in results]
    assert statistics.mean(deltas) > 0.5
    grew = sum(1 for r in results if r.overall_after > r.overall_before)
    assert grew > len(results) * 0.5


def test_old_players_decline_on_average():
    def make(i: int):
        return _skater_input(
            player_id=i,
            age=35,
            attrs={k: 70 for k in SKATER_ATTRIBUTES},
            potential=85,
        )
    results = _cohort(make)
    deltas = [r.overall_after - r.overall_before for r in results]
    assert statistics.mean(deltas) < -0.3


def test_soft_cap_growth_rare_but_not_zero():
    def make(i: int):
        return _skater_input(
            player_id=i,
            age=21,
            attrs={k: 90 for k in SKATER_ATTRIBUTES},
            potential=90,
        )
    results = _cohort(make, n=600)
    grew_count = sum(
        1 for r in results
        for ev in r.events if ev.delta > 0
    )
    assert 0 < grew_count < len(results) * 0.5


def test_early_bloomer_outgrows_late_bloomer_at_20():
    def make(player_id: int, dev: str):
        return _skater_input(
            player_id=player_id,
            age=20,
            attrs={k: 70 for k in SKATER_ATTRIBUTES},
            potential=88,
            development_type=dev,
        )
    early = [develop_player(make(i, "early_bloomer"), 7) for i in range(300)]
    late = [develop_player(make(i, "late_bloomer"), 7) for i in range(300)]
    early_mean = statistics.mean(r.overall_after - r.overall_before for r in early)
    late_mean = statistics.mean(r.overall_after - r.overall_before for r in late)
    assert early_mean > late_mean


def test_late_bloomer_outgrows_early_bloomer_at_27():
    def make(player_id: int, dev: str):
        return _skater_input(
            player_id=player_id,
            age=27,
            attrs={k: 75 for k in SKATER_ATTRIBUTES},
            potential=88,
            development_type=dev,
        )
    early = [develop_player(make(i, "early_bloomer"), 11) for i in range(300)]
    late = [develop_player(make(i, "late_bloomer"), 11) for i in range(300)]
    early_mean = statistics.mean(r.overall_after - r.overall_before for r in early)
    late_mean = statistics.mean(r.overall_after - r.overall_before for r in late)
    assert late_mean > early_mean


def test_boom_or_bust_has_higher_variance_than_steady():
    def make(player_id: int, dev: str):
        return _skater_input(
            player_id=player_id,
            age=22,
            attrs={k: 72 for k in SKATER_ATTRIBUTES},
            potential=88,
            development_type=dev,
        )
    boom = [develop_player(make(i, "boom_or_bust"), 13) for i in range(400)]
    steady = [develop_player(make(i, "steady"), 13) for i in range(400)]
    boom_var = statistics.pvariance(r.overall_after - r.overall_before for r in boom)
    steady_var = statistics.pvariance(r.overall_after - r.overall_before for r in steady)
    assert boom_var > steady_var


def test_perf_signal_above_average_helps_growth():
    def make(player_id: int, perf: float):
        return _skater_input(
            player_id=player_id,
            age=24,
            attrs={k: 75 for k in SKATER_ATTRIBUTES},
            potential=85,
            perf_signal=perf,
        )
    pos = [develop_player(make(i, 1.0), 5) for i in range(400)]
    neg = [develop_player(make(i, -1.0), 5) for i in range(400)]
    pos_mean = statistics.mean(r.overall_after - r.overall_before for r in pos)
    neg_mean = statistics.mean(r.overall_after - r.overall_before for r in neg)
    assert pos_mean > neg_mean


def test_no_events_means_plateau():
    def make(i: int):
        return _skater_input(
            player_id=i,
            age=31,
            attrs={k: 90 for k in SKATER_ATTRIBUTES},
            potential=90,
        )
    found_plateau = False
    for i in range(200):
        r = develop_player(make(i), season_seed=1)
        if not r.events:
            assert r.summary_reason == "plateau"
            found_plateau = True
    assert found_plateau, "expected at least one plateau outcome in cohort"


def test_mixed_takes_precedence_over_net_positive():
    events = (
        DevEvent(attribute="skating", old_value=70, new_value=72, delta=2, reason="growth"),
        DevEvent(attribute="defense", old_value=70, new_value=69, delta=-1, reason="decline"),
    )
    assert classify_summary(events, dev_type="steady") == "mixed"
