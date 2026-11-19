from __future__ import annotations

from autotube.pipelines.narrated_video.settings.output import ShortSceneSelection, ShortSettings
from autotube.pipelines.narrated_video.story.model import Story


def automatic_choice(story: Story) -> list[int]:
    if story.short_scenes:
        return list(story.short_scenes)
    heroes = [index for index, scene in enumerate(story.scenes) if scene.hero]
    return heroes or list(range(len(story.scenes)))


def short_scene_indexes(story: Story, settings: ShortSettings) -> list[int]:
    if settings.scene_selection is ShortSceneSelection.FIRST_N:
        chosen = list(range(min(settings.first_n_scenes, len(story.scenes))))
    else:
        chosen = automatic_choice(story)
    valid = sorted({index for index in chosen if 0 <= index < len(story.scenes)})
    return valid[: settings.max_scenes]
