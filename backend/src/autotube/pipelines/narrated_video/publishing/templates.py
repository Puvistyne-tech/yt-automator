from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story

METADATA_PLACEHOLDERS = (
    "title",
    "series",
    "tagline",
    "moral",
    "theme",
    "questions",
    "hashtags",
    "characters",
    "refrain",
    "hook",
)


def character_names(story: Story, settings: KidsStorySettings) -> str:
    members = settings.characters(story.character_ids)
    return ", ".join(member.name.for_language(story.language) for member in members)


def template_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:
    language = story.language
    return {
        "title": story.title,
        "series": settings.series.name.for_language(language),
        "tagline": settings.series.tagline.for_language(language),
        "moral": story.moral,
        "theme": story.theme,
        "questions": "\n".join(f"• {question}" for question in story.questions),
        "hashtags": " ".join(settings.metadata.hashtags.for_language(language)),
        "characters": character_names(story, settings),
        "refrain": settings.series.refrain.for_language(language),
        "hook": story.hook_line,
    }
