from datetime import date


def age_from_birth_date(birth_date: date, season_year: int) -> int:
    """Compute a player's age as of the given season year.

    Year-boundary aging only (no month/day adjustment) — keeps the model
    simple while we don't have a real calendar.
    """
    age = season_year - birth_date.year
    if age < 0:
        raise ValueError(f"season_year {season_year} predates birth year {birth_date.year}")
    return age
