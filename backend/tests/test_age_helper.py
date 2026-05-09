from datetime import date

import pytest

from app.services.player_age import age_from_birth_date


def test_age_at_year_simple():
    assert age_from_birth_date(date(2000, 1, 1), 2025) == 25


def test_age_birthday_in_year_treated_uniformly():
    # No month adjustment in v1; everyone "ages" on the year boundary.
    assert age_from_birth_date(date(2000, 12, 31), 2025) == 25


def test_age_negative_year_raises():
    with pytest.raises(ValueError):
        age_from_birth_date(date(2025, 1, 1), 2024)
