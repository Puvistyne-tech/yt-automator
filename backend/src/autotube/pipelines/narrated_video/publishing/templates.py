from __future__ import annotations

from autotube.pipelines.narrated_video.publishing.placeholder_values import common_values
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.structures.registry import spec_of


def template_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:
    extra = spec_of(settings).placeholder_values(story, settings)
    return {**common_values(story, settings), **extra}
