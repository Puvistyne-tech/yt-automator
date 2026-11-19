from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.repair_text import Repaired
from autotube.pipelines.narrated_video.structures.registry import spec_of


def repaired_script(story: Story, settings: KidsStorySettings) -> Repaired:
    notes: list[str] = []
    for repair in spec_of(settings).repairs:
        story, added = repair(story, settings)
        notes.extend(added)
    return story, tuple(notes)
