from __future__ import annotations

from functools import partial

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck
from autotube.pipelines.narrated_video.story.gates import (
    READING_GATES,
    SAFETY_GATES,
    CheckedGate,
    duration_problems,
    problems_of,
    scene_count_problems,
    words_per_scene_problems,
)
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.structures.length import duration_target, scene_range
from autotube.pipelines.narrated_video.structures.registry import spec_of

SIZE_GATES: tuple[CheckedGate, ...] = (
    (StoryCheck.SCENE_COUNT, partial(scene_count_problems, scene_range=scene_range)),
    (StoryCheck.WORDS_PER_SCENE, words_per_scene_problems),
    (StoryCheck.DURATION, partial(duration_problems, duration=duration_target)),
)


def story_problems(story: Story, settings: KidsStorySettings, seed: str = "") -> list[str]:
    extra = spec_of(settings).extra_gates(seed)
    gates = (*SIZE_GATES, *extra, *SAFETY_GATES, *READING_GATES)
    return problems_of(gates, story, settings)


def translation_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    extra = spec_of(settings).translation_gates
    return problems_of((*extra, *SAFETY_GATES), story, settings)
