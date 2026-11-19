from __future__ import annotations

from autotube.pipelines.narrated_video.languages import language_name
from autotube.pipelines.narrated_video.settings.base import (
    LONGEST_EPISODE,
    SHORTEST_EPISODE,
    StoryLanguage,
)
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.gates import (
    configured_duration,
    configured_scene_range,
)
from autotube.pipelines.narrated_video.story.reading import words_per_second
from autotube.pipelines.narrated_video.structures.registry import spec_of

Window = tuple[float, float]


def fixed_scene_count(settings: KidsStorySettings) -> int | None:
    fixed = spec_of(settings).fixed_scenes
    return None if fixed is None else fixed(settings)


def scene_range(settings: KidsStorySettings) -> tuple[int, int]:
    count = fixed_scene_count(settings)
    return configured_scene_range(settings) if count is None else (count, count)


def scene_line(settings: KidsStorySettings) -> str:
    low, high = scene_range(settings)
    return f"Exactly {low} scenes." if low == high else f"Between {low} and {high} scenes."


def spoken_window(settings: KidsStorySettings, language: str, scenes: int) -> Window:
    rules = settings.story
    per_second = words_per_second(rules.words_per_minute.for_language(language))
    low = rules.words_per_scene_min.for_language(language)
    high = rules.words_per_scene_max.for_language(language)
    return scenes * low / per_second, scenes * high / per_second


def fixed_window(settings: KidsStorySettings, language: str, scenes: int) -> Window:
    low, high = spoken_window(settings, language, scenes)
    return max(low, SHORTEST_EPISODE), min(high, LONGEST_EPISODE)


def duration_target(settings: KidsStorySettings, language: str) -> tuple[int, int]:
    count = fixed_scene_count(settings)
    if count is None:
        return configured_duration(settings, language)
    low, high = fixed_window(settings, language, count)
    return round((low + high) / 2), round((high - low) / 2)


def length_window(settings: KidsStorySettings, language: str) -> Window:
    target, tolerance = duration_target(settings, language)
    return target - tolerance, target + tolerance


def window_problem(settings: KidsStorySettings, language: str, scenes: int) -> str:
    low, high = fixed_window(settings, language, scenes)
    if low <= high:
        return ""
    spoken_low, spoken_high = spoken_window(settings, language, scenes)
    return (
        f"{scenes} scenes read in {spoken_low:.0f} to {spoken_high:.0f} s in "
        f"{language_name(language)} at these words per scene, but an episode lasts "
        f"{SHORTEST_EPISODE} to {LONGEST_EPISODE} s; choose another length or count"
    )


def reach_problem(settings: KidsStorySettings, language: str) -> str:
    fewest, most = scene_range(settings)
    shortest, longest = (
        spoken_window(settings, language, fewest)[0],
        spoken_window(settings, language, most)[1],
    )
    low, high = length_window(settings, language)
    if shortest <= high and longest >= low:
        return ""
    return (
        f"{fewest} to {most} scenes read in {shortest:.0f} to {longest:.0f} s in "
        f"{language_name(language)} at these words per scene, but the length is {low:.0f} to "
        f"{high:.0f} s; change the scene count, the words per scene or the length"
    )


def language_problem(settings: KidsStorySettings, language: str) -> str:
    count = fixed_scene_count(settings)
    if count is None:
        return reach_problem(settings, language)
    return window_problem(settings, language, count)


def length_problem(settings: KidsStorySettings) -> str:
    found = (language_problem(settings, language.value) for language in StoryLanguage)
    return next((problem for problem in found if problem), "")
