from __future__ import annotations

import re
from collections.abc import Mapping

from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story

PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def render_template(template: str, values: Mapping[str, str]) -> str:
    return PLACEHOLDER.sub(lambda match: values.get(match.group(1), match.group(0)), template)


def character_names(story: Story, settings: KidsStorySettings) -> str:
    ids = list(dict.fromkeys(name for scene in story.scenes for name in scene.characters))
    members = [member for name in ids if (member := settings.character(name)) is not None]
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
