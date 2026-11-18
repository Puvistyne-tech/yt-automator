from __future__ import annotations

import re
from collections.abc import Sequence

from automator.domain.model_base import DomainModel

TIMING = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})")
MILLIS_PER_SECOND = 1000


class SrtEntry(DomainModel):
    start: float
    end: float
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(self.lines)


def seconds_of(parts: Sequence[str]) -> float:
    hours, minutes, whole, millis = (int(part) for part in parts)
    return hours * 3600 + minutes * 60 + whole + millis / MILLIS_PER_SECOND


def parse_block(block: str) -> SrtEntry | None:
    lines = block.strip().splitlines()
    for index, line in enumerate(lines):
        timing = TIMING.search(line)
        if timing is not None:
            groups = timing.groups()
            return SrtEntry(
                start=seconds_of(groups[:4]),
                end=seconds_of(groups[4:]),
                lines=tuple(lines[index + 1 :]),
            )
    return None


def parse_srt(content: str) -> list[SrtEntry]:
    blocks = re.split(r"\n\s*\n", content.strip())
    return [entry for block in blocks if (entry := parse_block(block)) is not None]
