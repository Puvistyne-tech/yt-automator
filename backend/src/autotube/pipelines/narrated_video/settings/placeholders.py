from __future__ import annotations

from collections.abc import Iterable

from autotube.pipelines.narrated_video.settings.base import LocalizedText
from autotube.pipelines.narrated_video.text.templates import unknown_placeholders

THUMBNAIL_PLACEHOLDERS = ("title", "series", "moral", "hook")
CARD_PLACEHOLDERS = ("title", "series", "tagline", "moral", "hook", "refrain")


def unknown_placeholder_message(field: str, texts: Iterable[str], allowed: tuple[str, ...]) -> str:
    known = frozenset(allowed)
    unknown = sorted({name for text in texts for name in unknown_placeholders(text, known)})
    if not unknown:
        return ""
    named = ", ".join(f"{{{name}}}" for name in unknown)
    usable = " ".join(f"{{{name}}}" for name in allowed)
    return f"{field} has unknown placeholders {named}; use {usable}"


def checked_template(field: str, value: LocalizedText, allowed: tuple[str, ...]) -> LocalizedText:
    message = unknown_placeholder_message(field, value.model_dump().values(), allowed)
    if message:
        raise ValueError(message)
    return value
