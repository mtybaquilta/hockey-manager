from sim.models import SimGoalie
from sim.ratings import GOALIE_FORM_MAX, goalie_form_offset


def _goalie(mental: int) -> SimGoalie:
    return SimGoalie(id=42, reflexes=80, positioning=80, rebound_control=70, puck_handling=60, mental=mental)


def test_form_is_deterministic_for_same_seed_and_goalie():
    g = _goalie(50)
    assert goalie_form_offset(g, 1234) == goalie_form_offset(g, 1234)


def test_form_changes_with_seed():
    g = _goalie(50)
    samples = {goalie_form_offset(g, s) for s in range(20)}
    assert len(samples) > 1


def test_high_mental_dampens_variance():
    high = _goalie(100)
    low = _goalie(0)
    high_amp = max(abs(goalie_form_offset(high, s)) for s in range(50))
    low_amp = max(abs(goalie_form_offset(low, s)) for s in range(50))
    assert high_amp == 0.0
    assert low_amp > high_amp


def test_form_within_max_amplitude():
    g = _goalie(0)
    for s in range(100):
        assert abs(goalie_form_offset(g, s)) <= GOALIE_FORM_MAX + 1e-9
