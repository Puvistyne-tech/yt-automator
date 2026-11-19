from __future__ import annotations

from functools import partial

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck
from autotube.pipelines.narrated_video.story.gates import (
    LENGTH_GATES,
    READING_GATES,
    SAFETY_GATES,
    CheckedGate,
    problems_of,
    scene_count_problems,
)
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.structures.registry import spec_of


def size_gates(settings: KidsStorySettings) -> tuple[CheckedGate, ...]:
    counted = partial(scene_count_problems, scene_range=spec_of(settings).scene_range)
    return ((StoryCheck.SCENE_COUNT, counted), *LENGTH_GATES)


def story_problems(story: Story, settings: KidsStorySettings, seed: str = "") -> list[str]:
    extra = spec_of(settings).extra_gates(seed)
    gates = (*size_gates(settings), *extra, *SAFETY_GATES, *READING_GATES)
    return problems_of(gates, story, settings)


def translation_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    extra = spec_of(settings).translation_gates
    return problems_of((*extra, *SAFETY_GATES), story, settings)
