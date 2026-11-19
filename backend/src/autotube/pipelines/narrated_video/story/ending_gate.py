from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import says_moral, says_refrain
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.words import contains_phrase

MORAL_LINE = "the moral"
REFRAIN_LINE = "the refrain"


def ending_text(story: Story, scenes: int) -> str:
    return " ".join(scene.narration for scene in story.scenes[-scenes:])


def closing_scenes(count: int) -> str:
    return "the last scene" if count == 1 else f"the last {count} scenes"


def missing_ending_lines(story: Story, settings: KidsStorySettings) -> list[tuple[str, str]]:
    style = settings.story.ending_style
    ending = ending_text(story, settings.story.ending_scenes)
    refrain = settings.series.refrain.for_language(story.language)
    wanted = [
        (MORAL_LINE, story.moral, says_moral(style)),
        (REFRAIN_LINE, refrain, says_refrain(style) and bool(refrain.strip())),
    ]
    return [
        (name, line) for name, line, asked in wanted if asked and not contains_phrase(ending, line)
    ]


def ending_message(name: str, line: str, closing: str) -> str:
    if name == MORAL_LINE:
        return f"say the moral, word for word, in {closing}"
    return f'say the refrain "{line}" in {closing}'


def ending_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    closing = closing_scenes(settings.story.ending_scenes)
    missing = missing_ending_lines(story, settings)
    return [ending_message(name, line, closing) for name, line in missing]
