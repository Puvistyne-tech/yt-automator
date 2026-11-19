from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.bundled import BundledStory
from autotube.pipelines.narrated_video.story.reading import estimated_seconds
from autotube.pipelines.narrated_video.structures.length import length_window, scene_range


@dataclass(frozen=True)
class LengthWish:
    scenes: tuple[int, int]
    seconds: tuple[float, float]
    words_per_minute: float
    language: str
    refrain: str


def length_wish(settings: KidsStorySettings, language: str, refrain: str) -> LengthWish:
    rate = settings.story.words_per_minute.for_language(language)
    window = length_window(settings, language)
    return LengthWish(scene_range(settings), window, rate, language, refrain)


def bundled_seconds(story: BundledStory, wish: LengthWish) -> float:
    return estimated_seconds(story.to_story(wish.language, wish.refrain), wish.words_per_minute)


def scene_gap(story: BundledStory, wish: LengthWish) -> int:
    low, high = wish.scenes
    count = len(story.scenes)
    return max(low - count, count - high, 0)


def fits(story: BundledStory, wish: LengthWish) -> bool:
    low, high = wish.seconds
    return scene_gap(story, wish) == 0 and low <= bundled_seconds(story, wish) <= high


def length_pool(stories: Sequence[BundledStory], wish: LengthWish) -> list[BundledStory]:
    fitting = [story for story in stories if fits(story, wish)]
    if fitting:
        return fitting
    closest = min(scene_gap(story, wish) for story in stories)
    return [story for story in stories if scene_gap(story, wish) == closest]


def misfit_warning(story: BundledStory, wish: LengthWish) -> str:
    if fits(story, wish):
        return ""
    title = story.text[wish.language].title
    seconds = bundled_seconds(story, wish)
    (fewest, most), (low, high) = wish.scenes, wish.seconds
    return (
        f'the fallback story "{title}" has {len(story.scenes)} scenes and reads in about '
        f"{seconds:.0f} s, so it ignores the requested length of {fewest} to {most} scenes and "
        f"{low:.0f} to {high:.0f} s: no bundled story fits it"
    )
