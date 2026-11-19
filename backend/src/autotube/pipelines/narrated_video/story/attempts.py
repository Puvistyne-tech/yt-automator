from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from autotube.domain.model_base import JsonObject
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story, draft_dump
from autotube.pipelines.narrated_video.story.reading import estimated_seconds, total_words


@dataclass(frozen=True)
class Attempt:
    number: int
    language: str
    answer: str
    story: Story | None
    problems: tuple[str, ...]
    repairs: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.story is not None and not self.problems


AttemptKeeper = Callable[[Attempt], None]


def ignore_attempt(attempt: Attempt) -> None:  # noqa: ARG001
    return None


def attempt_measures(attempt: Attempt, settings: KidsStorySettings) -> str:
    if attempt.story is None:
        return f"an answer of {len(attempt.answer)} characters that is not a script"
    rate = settings.story.words_per_minute.for_language(attempt.language)
    seconds = estimated_seconds(attempt.story, rate)
    words, scenes = total_words(attempt.story), len(attempt.story.scenes)
    return f"{words} words, {scenes} scenes, about {seconds:.0f} s"


def attempt_record(attempt: Attempt) -> JsonObject:
    record: JsonObject = {
        "attempt": attempt.number,
        "language": attempt.language,
        "failed_checks": list(attempt.problems),
    }
    if attempt.story is None:
        return {**record, "answer": attempt.answer}
    return {**record, "script": draft_dump(attempt.story)}


def attempt_filename(attempt: Attempt) -> str:
    return f"attempt-{attempt.number}-{attempt.language}.json"
