from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import says_moral, says_refrain
from autotube.pipelines.narrated_video.story.gates import closing_scenes, ending_text
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.repair_text import (
    Repaired,
    unchanged,
    with_closing_lines,
)
from autotube.pipelines.narrated_video.story.words import contains_phrase


def missing_ending_lines(story: Story, settings: KidsStorySettings) -> list[tuple[str, str]]:
    style = settings.story.ending_style
    ending = ending_text(story, settings.story.ending_scenes)
    refrain = settings.series.refrain.for_language(story.language)
    wanted = [
        ("the moral", story.moral if says_moral(style) else ""),
        ("the refrain", refrain if says_refrain(style) else ""),
    ]
    return [
        (name, line) for name, line in wanted if line.strip() and not contains_phrase(ending, line)
    ]


def repaired_ending(story: Story, settings: KidsStorySettings) -> Repaired:
    missing = missing_ending_lines(story, settings)
    if not missing:
        return unchanged(story)
    names = " and ".join(name for name, _ in missing)
    closing = closing_scenes(settings.story.ending_scenes)
    note = f"added {names} to the last scene, as {closing} must say"
    return with_closing_lines(story, [line for _, line in missing]), (note,)
