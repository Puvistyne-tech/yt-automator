from __future__ import annotations

from collections.abc import Sequence

from autotube.domain.capabilities import WordTiming
from autotube.domain.srt import SrtEntry
from autotube.infrastructure.providers.media.ass_text import ass_line

TIME_TOLERANCE = 0.0005
HIDDEN = "{\\alpha&HFF&}"
SHOWN = "{\\alpha&H00&}"
Event = tuple[float, float, str]


def entry_words(entry: SrtEntry, words: Sequence[WordTiming]) -> list[WordTiming]:
    earliest, latest = entry.start - TIME_TOLERANCE, entry.end - TIME_TOLERANCE
    return [word for word in words if earliest <= word.start_seconds < latest]


def line_tokens(lines: Sequence[str]) -> list[list[str]]:
    return [line.split() for line in lines]


def only_spoken(tokens: list[list[str]], chosen: int) -> str:
    rendered: list[str] = []
    position = 0
    for line in tokens:
        parts: list[str] = []
        for token in line:
            text = ass_line(token)
            parts.append(f"{SHOWN}{text}{HIDDEN}" if position == chosen else text)
            position += 1
        rendered.append(" ".join(parts))
    return HIDDEN + "\\N".join(rendered)


def matched(tokens: list[list[str]], timed: Sequence[WordTiming]) -> bool:
    flat = [token for line in tokens for token in line]
    return bool(timed) and flat == [word.word for word in timed]


def karaoke_events(entry: SrtEntry, words: Sequence[WordTiming]) -> list[Event]:
    timed = entry_words(entry, words)
    tokens = line_tokens(entry.lines)
    if not matched(tokens, timed):
        return []
    ends = [word.start_seconds for word in timed[1:]] + [entry.end]
    return [
        (word.start_seconds, end, only_spoken(tokens, index))
        for index, (word, end) in enumerate(zip(timed, ends, strict=True))
        if end > word.start_seconds
    ]
