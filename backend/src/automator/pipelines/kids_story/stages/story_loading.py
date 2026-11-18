from __future__ import annotations

from automator.domain.pipeline import StageContext
from automator.pipelines.kids_story.artifacts import Role, path_of, read_json, required
from automator.pipelines.kids_story.languages import primary_language
from automator.pipelines.kids_story.stages.run_settings import kids_settings
from automator.pipelines.kids_story.story.model import Story


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
