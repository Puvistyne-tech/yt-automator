from __future__ import annotations

from collections.abc import Sequence

from automator.domain.srt import MILLIS_PER_SECOND
from automator.pipelines.kids_story.subtitles.cues import Cue


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
