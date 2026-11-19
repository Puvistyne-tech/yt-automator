from __future__ import annotations

from autotube.pipelines.narrated_video.settings.base import LocalizedText
from autotube.pipelines.narrated_video.text.templates import unknown_placeholders

THUMBNAIL_PLACEHOLDERS = ("title", "series", "moral", "hook")
CARD_PLACEHOLDERS = ("title", "series", "tagline", "moral", "hook", "refrain")


def checked_template(field: str, value: LocalizedText, allowed: tuple[str, ...]) -> LocalizedText:
    known = frozenset(allowed)
    texts = value.model_dump().values()
    unknown = sorted({name for text in texts for name in unknown_placeholders(text, known)})
    if unknown:
        named = ", ".join(f"{{{name}}}" for name in unknown)
        usable = " ".join(f"{{{name}}}" for name in allowed)
        raise ValueError(f"{field} has unknown placeholders {named}; use {usable}")
    return value
