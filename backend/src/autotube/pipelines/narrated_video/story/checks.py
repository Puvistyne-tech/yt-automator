from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.gates import (
    READING_GATES,
    SAFETY_GATES,
    SIZE_GATES,
    problems_of,
)
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.structures.registry import spec_of


def story_problems(story: Story, settings: KidsStorySettings, seed: str = "") -> list[str]:
    extra = spec_of(settings).extra_gates(seed)
    return problems_of((*SIZE_GATES, *extra, *SAFETY_GATES, *READING_GATES), story, settings)


def translation_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    extra = spec_of(settings).translation_gates
    return problems_of((*extra, *SAFETY_GATES), story, settings)
