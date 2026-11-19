from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story

COMMON_PLACEHOLDERS = ("title", "series", "tagline", "theme", "questions", "hashtags", "hook")
STORY_PLACEHOLDERS = ("moral", "characters", "refrain")


def character_names(story: Story, settings: KidsStorySettings) -> str:
    members = settings.characters(story.character_ids)
    return ", ".join(member.name.for_language(story.language) for member in members)


def common_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:
    language = story.language
    return {
        "title": story.title,
        "series": settings.series.name.for_language(language),
        "tagline": settings.series.tagline.for_language(language),
        "theme": story.theme,
        "questions": "\n".join(f"• {question}" for question in story.questions),
        "hashtags": " ".join(settings.metadata.hashtags.for_language(language)),
        "hook": story.hook_line,
    }


def story_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:
    return {
        "moral": story.moral,
        "characters": character_names(story, settings),
        "refrain": settings.series.refrain.for_language(story.language),
    }
