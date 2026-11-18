from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field

from automator.domain.capabilities import WordTiming
from automator.pipelines.kids_story.story.words import ends_sentence
from automator.pipelines.kids_story.text.graphemes import grapheme_clusters, grapheme_length


class CueRules(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_chars: int = Field(ge=1)
    max_lines: int = Field(ge=1)
    max_seconds: float = Field(gt=0)
    min_seconds: float = Field(ge=0)
    max_width: float = Field(default=math.inf, gt=0)
    measure: Callable[[str], float] | None = Field(default=None, exclude=True)

    def fits(self, line: str) -> bool:
        if grapheme_length(line) > self.max_chars:
            return False
        return self.measure is None or self.measure(line) <= self.max_width


class Cue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: float = Field(ge=0)
    end: float = Field(ge=0)
    lines: tuple[str, ...]
    limit: float = Field(ge=0)

    @property
    def text(self) -> str:
        return " ".join(self.lines)


def packed(units: Iterable[str], separator: str, fits: Callable[[str], bool]) -> list[str]:
    lines: list[str] = []
    for unit in units:
        joined = f"{lines[-1]}{separator}{unit}" if lines else unit
        if lines and fits(joined):
            lines[-1] = joined
        else:
            lines.append(unit)
    return lines


def pieces(word: str, rules: CueRules) -> list[str]:
    return [word] if rules.fits(word) else packed(grapheme_clusters(word), "", rules.fits)


def wrapped(words: Sequence[str], rules: CueRules) -> list[str]:
    return packed((piece for word in words for piece in pieces(word, rules)), " ", rules.fits)


def fits(group: Sequence[WordTiming], rules: CueRules) -> bool:
    within_lines = len(wrapped([word.word for word in group], rules)) <= rules.max_lines
    within_time = group[-1].end_seconds - group[0].start_seconds <= rules.max_seconds
    return within_lines and within_time


def word_groups(words: Sequence[WordTiming], rules: CueRules) -> list[list[WordTiming]]:
    groups: list[list[WordTiming]] = []
    current: list[WordTiming] = []
    for word in words:
        if current and not fits([*current, word], rules):
            groups.append(current)
            current = []
        current.append(word)
        if ends_sentence(word.word):
            groups.append(current)
            current = []
    return [*groups, current] if current else groups


def segment_cues(
    words: Sequence[WordTiming], offset: float, audio_seconds: float, rules: CueRules
) -> list[Cue]:
    limit = offset + audio_seconds
    cues = []
    for group in word_groups(words, rules):
        start = min(offset + group[0].start_seconds, limit)
        end = max(start, min(offset + group[-1].end_seconds, limit))
        lines = wrapped([word.word for word in group], rules)
        cues.extend(screenfuls(Cue(start=start, end=end, lines=(), limit=limit), lines, rules))
    return cues


def screenfuls(window: Cue, lines: Sequence[str], rules: CueRules) -> list[Cue]:
    chunks = [
        tuple(lines[at : at + rules.max_lines]) for at in range(0, len(lines), rules.max_lines)
    ]
    weights = [sum(grapheme_length(line) for line in chunk) for chunk in chunks]
    total = sum(weights) or 1
    span = window.end - window.start
    cues: list[Cue] = []
    start = window.start
    for chunk, weight in zip(chunks, weights, strict=True):
        end = start + span * weight / total
        cues.append(window.model_copy(update={"start": start, "end": end, "lines": chunk}))
        start = end
    return cues


def separated(cues: Sequence[Cue], min_seconds: float) -> list[Cue]:
    ordered = sorted(cues, key=lambda cue: cue.start)
    result: list[Cue] = []
    for index, cue in enumerate(ordered):
        following = ordered[index + 1].start if index + 1 < len(ordered) else None
        ceiling = cue.limit if following is None else min(cue.limit, following)
        end = min(max(cue.end, cue.start + min_seconds), ceiling)
        if end > cue.start:
            result.append(cue.model_copy(update={"end": end}))
    return result
