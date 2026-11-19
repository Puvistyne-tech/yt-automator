from __future__ import annotations

from autotube.domain.quality import ScoreItem
from autotube.pipelines.narrated_video.scoring.content_items import gate_item
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck
from autotube.pipelines.narrated_video.story.gates import CheckedGate
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.words import contains_phrase

QUESTION_MARKS = ("?", "？")


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


EXPLAINER_GATES: tuple[CheckedGate, ...] = ((StoryCheck.STRUCTURE, explainer_problems),)


def explainer_seeded_gates(seed: str) -> tuple[CheckedGate, ...]:  # noqa: ARG001
    return EXPLAINER_GATES


def explainer_shape(inputs: ScoreInputs) -> ScoreItem | None:
    weight = inputs.settings.quality.weights.structure
    return gate_item(inputs, "structure", "Explainer hook and takeaway", weight, explainer_problems)
