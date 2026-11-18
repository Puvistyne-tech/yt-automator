from __future__ import annotations

from automator.domain.pipeline import StageContext
from automator.pipelines.kids_story.artifacts import Role, path_of, read_json, required
from automator.pipelines.kids_story.languages import primary_language
from automator.pipelines.kids_story.settings.output import size_of
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story

PNG = "image/png"
JSON = "application/json"
WAV = "audio/wav"
MP4 = "video/mp4"
SRT = "application/x-subrip"


def kids_settings(context: StageContext) -> KidsStorySettings:
    if not isinstance(context.settings, KidsStorySettings):
        raise TypeError("kids_story stages need KidsStorySettings")
    return context.settings


def load_story(context: StageContext, language: str) -> Story:
    found = required(context.artifacts, Role.STORY, language)
    return Story.model_validate(read_json(path_of(context, found)))


def load_stories(context: StageContext) -> dict[str, Story]:
    return {language: load_story(context, language) for language in context.languages}


def art_story(context: StageContext) -> Story:
    settings = kids_settings(context)
    return load_story(
        context, primary_language(settings.story.primary_language.value, context.languages)
    )


def episode_size(settings: KidsStorySettings) -> tuple[int, int]:
    return size_of(settings.episode.resolution)


def short_size(settings: KidsStorySettings) -> tuple[int, int]:
    return size_of(settings.short.resolution)
