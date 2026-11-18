from __future__ import annotations

from collections.abc import Callable, Iterable


def packed(units: Iterable[str], separator: str, fits: Callable[[str], bool]) -> list[str]:
    lines: list[str] = []
    for unit in units:
        joined = f"{lines[-1]}{separator}{unit}" if lines else unit
        if lines and fits(joined):
            lines[-1] = joined
        else:
            lines.append(unit)
    return lines
