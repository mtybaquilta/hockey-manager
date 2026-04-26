REGULATION_TICKS = 60


def _build_pattern(weights: list[tuple[int, int]]) -> tuple[int, ...]:
    out: list[int] = []
    for line, count in weights:
        out.extend([line] * count)
    return tuple(out)


_FWD_PATTERN: tuple[int, ...] = _build_pattern([(0, 24), (1, 18), (2, 12), (3, 6)])
_DEF_PATTERN: tuple[int, ...] = _build_pattern([(0, 27), (1, 21), (2, 12)])


def forward_line_at_tick(tick: int) -> int:
    return _FWD_PATTERN[tick % REGULATION_TICKS]


def defense_pair_at_tick(tick: int) -> int:
    return _DEF_PATTERN[tick % REGULATION_TICKS]
