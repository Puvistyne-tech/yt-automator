from __future__ import annotations

from autotube.domain.pipeline import StageContext
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings


def kids_settings(context: StageContext) -> KidsStorySettings:
    if not isinstance(context.settings, KidsStorySettings):
        raise TypeError("kids_story stages need KidsStorySettings")
    return context.settings
