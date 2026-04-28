TICKS_PER_PERIOD = 60
PERIODS = 3
REGULATION_TICKS = TICKS_PER_PERIOD * PERIODS  # 180


def period_at_tick(tick: int) -> int:
    """1-indexed period; overtime ticks return PERIODS + 1."""
    if tick >= REGULATION_TICKS:
        return PERIODS + 1
    return tick // TICKS_PER_PERIOD + 1


def _build_pattern(weights: list[tuple[int, int]]) -> tuple[int, ...]:
    out: list[int] = []
    for line, count in weights:
        out.extend([line] * count)
    return tuple(out)


_FWD_PATTERN: tuple[int, ...] = _build_pattern([(0, 72), (1, 54), (2, 36), (3, 18)])
_DEF_PATTERN: tuple[int, ...] = _build_pattern([(0, 81), (1, 63), (2, 36)])


def forward_line_at_tick(tick: int) -> int:
    return _FWD_PATTERN[tick % REGULATION_TICKS]


def defense_pair_at_tick(tick: int) -> int:
    return _DEF_PATTERN[tick % REGULATION_TICKS]
