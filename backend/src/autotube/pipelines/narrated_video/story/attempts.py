from __future__ import annotations

from dataclasses import dataclass

from autotube.pipelines.narrated_video.story.model import Story


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
