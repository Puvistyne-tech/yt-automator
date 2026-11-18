from __future__ import annotations

from collections.abc import Sequence

from autotube.pipelines.kids_story.settings.story import StorySettings, ThemeMode
from autotube.shared.hashing import sha256_hex


def stable_index(seed: str, size: int) -> int:
    return int(sha256_hex(seed)[:12], 16) % size if size > 0 else 0


def recent_keys(recent: Sequence[str], count: int) -> set[str]:
    window = list(recent)[-count:] if count > 0 else []
    return {theme.casefold() for theme in window}


def fresh_items(items: Sequence[str], recent: Sequence[str], count: int) -> list[str]:
    avoided = recent_keys(recent, count)
    fresh = [item for item in items if item.casefold() not in avoided]
    return fresh or list(items)


def choose_theme(settings: StorySettings, seed: str) -> str:
    if settings.theme_mode is ThemeMode.FIXED or not settings.themes:
        return settings.fixed_theme
    candidates = fresh_items(settings.themes, settings.recent_themes, settings.avoid_repeat_last)
    return candidates[stable_index(seed, len(candidates))]
