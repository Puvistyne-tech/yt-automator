from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.words import contains_phrase
from autotube.pipelines.narrated_video.structures.framing import QUESTION_MARKS


def hook_problems(story: Story, settings: KidsStorySettings) -> list[str]:  # noqa: ARG001
    opening = story.scenes[0].narration
    if any(mark in opening for mark in QUESTION_MARKS):
        return []
    return ["open the first scene with the question this video answers"]


def takeaway_problems(story: Story, settings: KidsStorySettings) -> list[str]:  # noqa: ARG001
    if contains_phrase(story.scenes[-1].narration, story.moral):
        return []
    return ["say the takeaway, word for word, in the last scene"]


def explainer_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    return [*hook_problems(story, settings), *takeaway_problems(story, settings)]
