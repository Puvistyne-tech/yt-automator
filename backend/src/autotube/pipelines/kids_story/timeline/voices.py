from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, JsonValue

from autotube.domain.capabilities import TimingSource, WordTiming
from autotube.domain.run_parts import Artifact
from autotube.pipelines.kids_story.artifacts import Role, number, text, with_role


class VoiceLine(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    segment: str
    filename: str
    seconds: float
    text: str
    words: tuple[WordTiming, ...] = ()
    timing_source: TimingSource = TimingSource.ESTIMATE


def timings_meta(words: Sequence[WordTiming]) -> list[JsonValue]:
    return [
        {"word": word.word, "start": word.start_seconds, "end": word.end_seconds} for word in words
    ]


def timing_of(entry: JsonValue) -> WordTiming | None:
    if not isinstance(entry, dict):
        return None
    return WordTiming(
        word=text(entry.get("word")),
        start_seconds=number(entry.get("start")),
        end_seconds=number(entry.get("end")),
    )


def words_of_meta(value: JsonValue) -> tuple[WordTiming, ...]:
    entries = value if isinstance(value, list) else []
    return tuple(timing for entry in entries if (timing := timing_of(entry)) is not None)


def voice_line(found: Artifact) -> VoiceLine:
    source = text(found.meta.get("timing_source"))
    return VoiceLine(
        segment=text(found.meta.get("segment")),
        filename=found.filename,
        seconds=number(found.meta.get("duration_seconds")),
        text=text(found.meta.get("text")),
        words=words_of_meta(found.meta.get("words")),
        timing_source=TimingSource(source)
        if source in set(TimingSource)
        else TimingSource.ESTIMATE,
    )


def voice_lines(artifacts: Sequence[Artifact], language: str) -> dict[str, VoiceLine]:
    lines = [voice_line(found) for found in with_role(artifacts, Role.NARRATION, language)]
    return {line.segment: line for line in lines}
