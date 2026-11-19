from __future__ import annotations

import re

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story, StoryScene
from autotube.pipelines.narrated_video.story.repair_text import (
    Repaired,
    unchanged,
    with_closing_lines,
)
from autotube.pipelines.narrated_video.story.words import contains_phrase
from autotube.pipelines.narrated_video.structures.explainer_checks import wants_takeaway
from autotube.pipelines.narrated_video.structures.framing import QUESTION_MARKS
from autotube.pipelines.narrated_video.structures.list_checks import expected_numbers
from autotube.pipelines.narrated_video.structures.quiz_checks import asks

DIGITS = re.compile(r"\d+")
QUESTION_MARK = QUESTION_MARKS[0]


def repaired_takeaway(story: Story, settings: KidsStorySettings) -> Repaired:
    takeaway = story.moral.strip()
    last = story.scenes[-1].narration
    if not wants_takeaway(settings) or not takeaway or contains_phrase(last, takeaway):
        return unchanged(story)
    return with_closing_lines(story, [takeaway]), ("added the takeaway to the last scene",)


def agrees(scene: StoryScene, number: int) -> bool:
    spoken = DIGITS.findall(scene.narration)
    return not spoken or str(number) in spoken


def renumbered(story: Story, numbers: list[int]) -> list[StoryScene]:
    items = [
        scene.model_copy(update={"number": number})
        for scene, number in zip(story.scenes[1:-1], numbers, strict=True)
    ]
    ends = [
        scene.model_copy(update={"number": None}) for scene in (story.scenes[0], story.scenes[-1])
    ]
    return [ends[0], *items, ends[1]]


def repaired_numbers(story: Story, settings: KidsStorySettings, descending: bool) -> Repaired:
    items = story.scenes[1:-1]
    numbers = expected_numbers(settings.story.item_count, descending)
    current = [story.scenes[0].number, *(scene.number for scene in items), story.scenes[-1].number]
    if len(items) != len(numbers) or current == [None, *numbers, None]:
        return unchanged(story)
    if not all(agrees(scene, number) for scene, number in zip(items, numbers, strict=True)):
        return unchanged(story)
    fixed = story.model_copy(update={"scenes": renumbered(story, numbers)})
    return fixed, ("numbered the list items in order",)


def marked(scene: StoryScene) -> StoryScene:
    question = scene.question.rstrip()
    if not asks(scene) or question.endswith(QUESTION_MARKS):
        return scene
    return scene.model_copy(update={"question": f"{question}{QUESTION_MARK}"})


def repaired_question_marks(story: Story, settings: KidsStorySettings) -> Repaired:  # noqa: ARG001
    scenes = [marked(scene) for scene in story.scenes]
    if scenes == story.scenes:
        return unchanged(story)
    fixed = story.model_copy(update={"scenes": scenes})
    return fixed, ("ended every quiz question with a question mark",)
