from __future__ import annotations

import math
from dataclasses import dataclass

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.reading import SECONDS_PER_MINUTE, word_range
from autotube.pipelines.narrated_video.structures.length import (
    duration_target,
    length_window,
    scene_range,
)

Span = tuple[int, int]


@dataclass(frozen=True)
class WordBudget:
    total: Span
    target: int
    per_scene: Span


def configured_words(settings: KidsStorySettings, language: str) -> Span:
    rules = settings.story
    low = rules.words_per_scene_min.for_language(language)
    high = rules.words_per_scene_max.for_language(language)
    return math.ceil(low), math.floor(high)


def within(span: Span, limits: Span) -> Span | None:
    low, high = max(span[0], limits[0]), min(span[1], limits[1])
    return (low, high) if low <= high else None


def per_scene_words(total: Span, scenes: Span, configured: Span) -> Span:
    fewest, most = scenes
    every_count = (math.ceil(total[0] / fewest), math.floor(total[1] / most))
    some_count = (math.ceil(total[0] / most), math.floor(total[1] / fewest))
    fits = (within(span, configured) for span in (every_count, some_count))
    return next((span for span in fits if span is not None), configured)


def word_budget(settings: KidsStorySettings, language: str) -> WordBudget:
    rate = settings.story.words_per_minute.for_language(language)
    total = word_range(*length_window(settings, language), rate)
    target_seconds, _ = duration_target(settings, language)
    target = round(target_seconds * rate / SECONDS_PER_MINUTE)
    scenes = scene_range(settings)
    per_scene = per_scene_words(total, scenes, configured_words(settings, language))
    return WordBudget(total, target, per_scene)
