from __future__ import annotations

from collections.abc import Callable

from autotube.pipelines.narrated_video.story.model import Story, StoryScene

FRAMING_SCENES = 2
QUESTION_MARKS = ("?", "？")


def framing_problems(story: Story, plain: Callable[[StoryScene], bool], message: str) -> list[str]:
    ends = (story.scenes[0], story.scenes[-1])
    if len(story.scenes) > 1 and all(plain(scene) for scene in ends):
        return []
    return [message]
