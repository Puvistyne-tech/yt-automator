from __future__ import annotations

from autotube.pipelines.kids_story.settings.cast import Character
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.settings.story_controls import LeadMode
from autotube.pipelines.kids_story.story.themes import stable_index


def lead_index(settings: KidsStorySettings, seed: str) -> int:
    if settings.story.lead_mode is LeadMode.FIXED:
        return 0
    return stable_index(f"lead:{seed}", len(settings.cast))


def episode_cast(settings: KidsStorySettings, seed: str) -> list[Character]:
    cast = settings.cast
    size = min(settings.story.cast_per_episode or len(cast), len(cast))
    start = lead_index(settings, seed)
    return [cast[(start + offset) % len(cast)] for offset in range(size)]
