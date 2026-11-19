from __future__ import annotations

from collections.abc import Sequence

from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.words import ends_sentence

Repaired = tuple[Story, tuple[str, ...]]
SENTENCE_END = "."


def as_sentence(text: str) -> str:
    kept = text.strip()
    words = kept.split()
    return kept if not words or ends_sentence(words[-1]) else f"{kept}{SENTENCE_END}"


def with_lines(narration: str, lines: Sequence[str]) -> str:
    return " ".join(as_sentence(part) for part in (narration, *lines) if part.strip())


def with_closing_lines(story: Story, lines: Sequence[str]) -> Story:
    last = story.scenes[-1]
    closed = last.model_copy(update={"narration": with_lines(last.narration, lines)})
    return story.model_copy(update={"scenes": [*story.scenes[:-1], closed]})


def unchanged(story: Story) -> Repaired:
    return story, ()
