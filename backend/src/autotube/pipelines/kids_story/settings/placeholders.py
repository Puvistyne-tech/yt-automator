from __future__ import annotations

from collections.abc import Collection

from autotube.pipelines.kids_story.settings.base import LocalizedText
from autotube.pipelines.kids_story.text.templates import PLACEHOLDER

THUMBNAIL_PLACEHOLDERS = ("title", "series", "moral", "hook")
CARD_PLACEHOLDERS = ("title", "series", "tagline", "moral", "hook", "refrain")


def unknown_placeholders(template: str, allowed: Collection[str]) -> list[str]:
    return [name for name in PLACEHOLDER.findall(template) if name not in allowed]


def checked_template(field: str, value: LocalizedText, allowed: Collection[str]) -> LocalizedText:
    unknown = sorted(
        {
            name
            for text in value.model_dump().values()
            for name in unknown_placeholders(text, allowed)
        }
    )
    if unknown:
        named = ", ".join(f"{{{name}}}" for name in unknown)
        usable = " ".join(f"{{{name}}}" for name in allowed)
        raise ValueError(f"{field} has unknown placeholders {named}; use {usable}")
    return value
