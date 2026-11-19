from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.ending_gate import (
    closing_scenes,
    missing_ending_lines,
)
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.repair_text import (
    Repaired,
    unchanged,
    with_closing_lines,
)


def repaired_ending(story: Story, settings: KidsStorySettings) -> Repaired:
    missing = [(name, line) for name, line in missing_ending_lines(story, settings) if line.strip()]
    if not missing:
        return unchanged(story)
    names = " and ".join(name for name, _ in missing)
    closing = closing_scenes(settings.story.ending_scenes)
    note = f"added {names} to the last scene, as {closing} must say"
    return with_closing_lines(story, [line for _, line in missing]), (note,)
