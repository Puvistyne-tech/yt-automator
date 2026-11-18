from __future__ import annotations

MIN_EVEN_SIZE = 2


def even(size: int) -> int:
    return max(MIN_EVEN_SIZE, size - size % 2)
