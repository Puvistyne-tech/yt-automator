from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from automator.domain.capabilities import WordTiming
from automator.pipelines.kids_story.subtitles.cues import Cue, CueRules, word_groups, wrapped
from automator.pipelines.kids_story.text.graphemes import grapheme_length

Screen = tuple[str, ...]


@dataclass(frozen=True)
class Window:
    start: float
    end: float
    room: float
    limit: float


def chunked(lines: Sequence[str], size: int) -> list[Screen]:
    return [tuple(lines[at : at + size]) for at in range(0, len(lines), size)]


def screen_count(window: Window, wanted: int, min_seconds: float) -> int:
    if min_seconds <= 0:
        return wanted
    return max(1, min(wanted, int((window.room - window.start) / min_seconds)))


def merged(screens: list[Screen], count: int) -> list[Screen]:
    rest = tuple(line for screen in screens[count - 1 :] for line in screen)
    return [*screens[: count - 1], rest]


def durations(span: float, weights: Sequence[int], minimum: float) -> list[float]:
    floor = minimum * len(weights)
    if span <= floor:
        return [span / len(weights)] * len(weights)
    total = sum(weights)
    return [minimum + (span - floor) * weight / total for weight in weights]


def screenfuls(window: Window, lines: Sequence[str], rules: CueRules) -> list[Cue]:
    screens = chunked(lines, rules.max_lines)
    if not screens:
        return []
    count = screen_count(window, len(screens), rules.min_seconds)
    screens = merged(screens, count) if count < len(screens) else screens
    needed = window.start + rules.min_seconds * len(screens)
    end = min(window.room, max(window.end, needed))
    weights = [max(1, sum(grapheme_length(line) for line in screen)) for screen in screens]
    seconds_each = durations(end - window.start, weights, rules.min_seconds)
    cues: list[Cue] = []
    start = window.start
    for screen, seconds in zip(screens, seconds_each, strict=True):
        cues.append(Cue(start=start, end=start + seconds, lines=screen, limit=window.limit))
        start += seconds
    return cues


def late_joined(
    groups: list[list[WordTiming]], offset: float, latest: float
) -> list[list[WordTiming]]:
    early = [group for group in groups if offset + group[0].start_seconds < latest]
    late = [word for group in groups if offset + group[0].start_seconds >= latest for word in group]
    return [*early, late] if late else early


def segment_cues(
    words: Sequence[WordTiming], offset: float, audio_seconds: float, rules: CueRules
) -> list[Cue]:
    limit = offset + audio_seconds
    latest = max(offset, limit - rules.min_seconds)
    groups = late_joined(word_groups(words, rules), offset, latest)
    starts = [min(offset + group[0].start_seconds, latest) for group in groups]
    cues: list[Cue] = []
    for group, start, following in zip(groups, starts, [*starts, limit][1:], strict=True):
        room = max(following, start)
        end = min(max(start, min(offset + group[-1].end_seconds, limit)), room)
        window = Window(start=start, end=end, room=room, limit=limit)
        cues.extend(screenfuls(window, wrapped([word.word for word in group], rules), rules))
    return cues
