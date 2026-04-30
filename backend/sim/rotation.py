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


def build_rotation_schedule(
    total_ticks: int, distribution: tuple[float, ...]
) -> tuple[int, ...]:
    """Return a deterministic per-tick schedule of line indices.

    Each line index appears `round(total_ticks * distribution[i])` times,
    with the largest bucket adjusted so the counts sum to total_ticks.
    Indices are interleaved (Bresenham-style) so any short window
    approximates the configured distribution.
    """
    if total_ticks <= 0:
        return ()
    n = len(distribution)
    if n == 0:
        return tuple([0] * total_ticks)

    counts = [round(total_ticks * w) for w in distribution]
    diff = total_ticks - sum(counts)
    if diff != 0:
        idx = max(range(n), key=lambda i: counts[i])
        counts[idx] += diff
    counts = [max(0, c) for c in counts]
    if sum(counts) == 0:
        return tuple([0] * total_ticks)
    while sum(counts) < total_ticks:
        idx = max(range(n), key=lambda i: counts[i])
        counts[idx] += 1
    while sum(counts) > total_ticks:
        idx = max(range(n), key=lambda i: counts[i])
        counts[idx] -= 1

    # Largest-remainder per-tick scheduling (Bresenham-style across N lanes).
    # At each tick, place the bucket whose ideal cumulative count is most ahead
    # of its actual placements, while still having budget remaining.
    placed = [0] * n
    out: list[int] = []
    for t in range(total_ticks):
        ideal_after = [(t + 1) * counts[i] / total_ticks for i in range(n)]
        best_i = -1
        best_err = -1e18
        for i in range(n):
            if placed[i] >= counts[i]:
                continue
            err = ideal_after[i] - placed[i]
            if err > best_err + 1e-12:
                best_err = err
                best_i = i
        if best_i < 0:
            best_i = next(i for i in range(n) if placed[i] < counts[i])
        out.append(best_i)
        placed[best_i] += 1
    return tuple(out)
