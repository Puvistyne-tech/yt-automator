from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from automator.domain.capabilities import WordTiming
from automator.pipelines.kids_story.story.words import ends_sentence
from automator.pipelines.kids_story.text.graphemes import grapheme_length, split_clusters


class CueRules(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_chars: int = Field(ge=1)
    max_lines: int = Field(ge=1)
    max_seconds: float = Field(gt=0)
    min_seconds: float = Field(ge=0)


class Cue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: float = Field(ge=0)
    end: float = Field(ge=0)
    lines: tuple[str, ...]
    limit: float = Field(ge=0)

    @property
    def text(self) -> str:
        return " ".join(self.lines)


def pieces(word: str, max_chars: int) -> list[str]:
    return split_clusters(word, max_chars) if grapheme_length(word) > max_chars else [word]


def wrapped(words: Sequence[str], max_chars: int) -> list[str]:
    lines: list[str] = []
    for word in words:
        for piece in pieces(word, max_chars):
            joined = f"{lines[-1]} {piece}" if lines else piece
            if lines and grapheme_length(joined) <= max_chars:
                lines[-1] = joined
            else:
                lines.append(piece)
    return lines


def fits(group: Sequence[WordTiming], rules: CueRules) -> bool:
    within_lines = len(wrapped([word.word for word in group], rules.max_chars)) <= rules.max_lines
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
        end = min(offset + group[-1].end_seconds, limit)
        lines = tuple(wrapped([word.word for word in group], rules.max_chars))
        cues.append(Cue(start=start, end=max(start, end), lines=lines, limit=limit))
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
