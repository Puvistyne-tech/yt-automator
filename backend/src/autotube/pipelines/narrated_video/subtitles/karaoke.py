from __future__ import annotations

from collections.abc import Sequence

from autotube.domain.capabilities import WordTiming
from autotube.pipelines.narrated_video.subtitles.cues import Cue, CueRules, pieces

MILLIS = 3


def split_word(word: WordTiming, offset: float, rules: CueRules) -> list[WordTiming]:
    parts = pieces(word.word, rules)
    step = (word.end_seconds - word.start_seconds) / len(parts)
    start = offset + word.start_seconds
    return [
        WordTiming(
            word=part,
            start_seconds=start + step * index,
            end_seconds=start + step * (index + 1),
        )
        for index, part in enumerate(parts)
    ]


def timed_pieces(group: Sequence[WordTiming], offset: float, rules: CueRules) -> list[WordTiming]:
    return [part for word in group for part in split_word(word, offset, rules)]


def token_count(cue: Cue) -> int:
    return sum(len(line.split()) for line in cue.lines)


def with_words(cues: Sequence[Cue], timed: Sequence[WordTiming]) -> list[Cue]:
    attached: list[Cue] = []
    cursor = 0
    for cue in cues:
        count = token_count(cue)
        attached.append(cue.model_copy(update={"words": tuple(timed[cursor : cursor + count])}))
        cursor += count
    return attached


def clamped(word: WordTiming, cue: Cue) -> WordTiming | None:
    start = round(max(word.start_seconds, cue.start), MILLIS)
    end = round(cue.end, MILLIS)
    if start >= end:
        return None
    finish = max(start, round(min(word.end_seconds, cue.end), MILLIS))
    return WordTiming(word=word.word, start_seconds=start, end_seconds=finish)


def karaoke_words(cues: Sequence[Cue]) -> tuple[WordTiming, ...]:
    return tuple(
        timing for cue in cues for word in cue.words if (timing := clamped(word, cue)) is not None
    )
