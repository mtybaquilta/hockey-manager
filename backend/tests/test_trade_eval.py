from app.services.trade_eval import age_modifier, potential_modifier


def test_age_modifier_brackets():
    assert age_modifier(20) == 4
    assert age_modifier(25) == 2
    assert age_modifier(29) == 0
    assert age_modifier(33) == -2
    assert age_modifier(36) == -5


def test_potential_modifier_young_high_potential():
    assert potential_modifier(potential=92, age=21) == 6
    assert potential_modifier(potential=86, age=22) == 4
    assert potential_modifier(potential=86, age=25) == 2
    assert potential_modifier(potential=78, age=31) == -1
    assert potential_modifier(potential=80, age=27) == 0
