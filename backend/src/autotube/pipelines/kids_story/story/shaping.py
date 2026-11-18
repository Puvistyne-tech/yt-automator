from __future__ import annotations

from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.story.model import Story, StoryScene


def limited_heroes(scenes: list[StoryScene], count: int) -> list[StoryScene]:
    kept: list[StoryScene] = []
    heroes = 0
    for scene in scenes:
        keep_hero = scene.hero and heroes < count
        heroes += int(keep_hero)
        kept.append(scene if scene.hero == keep_hero else scene.model_copy(update={"hero": False}))
    return kept


def valid_short_scenes(story: Story) -> list[int]:
    seen: list[int] = []
    for index in story.short_scenes:
        if 0 <= index < len(story.scenes) and index not in seen:
            seen.append(index)
    return seen


def shaped(story: Story, settings: KidsStorySettings) -> Story:
    return story.model_copy(
        update={
            "scenes": limited_heroes(story.scenes, settings.visuals.hero_scene_count),
            "questions": story.questions[: settings.story.question_count],
            "short_scenes": valid_short_scenes(story),
        }
    )
