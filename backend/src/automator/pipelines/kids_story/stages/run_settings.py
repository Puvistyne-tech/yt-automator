from __future__ import annotations

from automator.domain.pipeline import StageContext
from automator.pipelines.kids_story.settings.root import KidsStorySettings


def kids_settings(context: StageContext) -> KidsStorySettings:
    if not isinstance(context.settings, KidsStorySettings):
        raise TypeError("kids_story stages need KidsStorySettings")
    return context.settings
