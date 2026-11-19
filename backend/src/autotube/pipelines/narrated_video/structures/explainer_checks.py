from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import says_moral
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.words import contains_phrase
from autotube.pipelines.narrated_video.structures.framing import QUESTION_MARKS

MISSING_TAKEAWAY = 'write the takeaway in "moral"'
UNSAID_TAKEAWAY = "say the takeaway, word for word, in the last scene"


def wants_takeaway(settings: KidsStorySettings) -> bool:
    return says_moral(settings.story.ending_style)


def hook_problems(story: Story, settings: KidsStorySettings) -> list[str]:  # noqa: ARG001
    opening = story.scenes[0].narration
    if any(mark in opening for mark in QUESTION_MARKS):
        return []
    return ["open the first scene with the question this video answers"]


def takeaway_field_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    if not wants_takeaway(settings) or story.moral.strip():
        return []
    return [MISSING_TAKEAWAY]


def takeaway_unsaid(story: Story, settings: KidsStorySettings) -> bool:
    return wants_takeaway(settings) and not contains_phrase(story.scenes[-1].narration, story.moral)


def takeaway_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    return [UNSAID_TAKEAWAY] if takeaway_unsaid(story, settings) else []


def explainer_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    return [*hook_problems(story, settings), *takeaway_problems(story, settings)]
