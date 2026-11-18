from __future__ import annotations

import re
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from automator.pipelines.kids_story.subtitles.cues import Cue

TIMING = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})")
MILLIS_PER_SECOND = 1000


class SrtEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: float
    end: float
    text: str


def timestamp(seconds: float) -> str:
    millis = round(max(seconds, 0.0) * MILLIS_PER_SECOND)
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    whole, millis = divmod(rest, MILLIS_PER_SECOND)
    return f"{hours:02d}:{minutes:02d}:{whole:02d},{millis:03d}"


def render_srt(cues: Sequence[Cue]) -> str:
    blocks = [
        f"{number}\n{timestamp(cue.start)} --> {timestamp(cue.end)}\n" + "\n".join(cue.lines)
        for number, cue in enumerate(cues, start=1)
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


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
                text=" ".join(lines[index + 1 :]),
            )
    return None


def parse_srt(content: str) -> list[SrtEntry]:
    blocks = re.split(r"\n\s*\n", content.strip())
    return [entry for block in blocks if (entry := parse_block(block)) is not None]
