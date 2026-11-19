from __future__ import annotations

from collections.abc import Callable

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import (
    StoryCheck,
    says_moral,
    says_refrain,
)
from autotube.pipelines.narrated_video.story.casting import episode_cast
from autotube.pipelines.narrated_video.story.child_terms import (
    child_term_message,
    child_terms_in_any,
)
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.reading import (
    estimated_seconds,
    narration_of,
    reading_metrics,
)
from autotube.pipelines.narrated_video.story.words import contains_phrase, word_count

Gate = Callable[[Story, KidsStorySettings], list[str]]
SceneRange = Callable[[KidsStorySettings], tuple[int, int]]
DurationTarget = Callable[[KidsStorySettings, str], tuple[int, int]]


def configured_scene_range(settings: KidsStorySettings) -> tuple[int, int]:
    return settings.story.scene_count_min, settings.story.scene_count_max


def scene_count_problems(
    story: Story, settings: KidsStorySettings, scene_range: SceneRange = configured_scene_range
) -> list[str]:
    low, high = scene_range(settings)
    found = len(story.scenes)
    if low <= found <= high:
        return []
    wanted = f"exactly {low}" if low == high else f"between {low} and {high}"
    return [f"use {wanted} scenes, not {found}"]


def words_per_scene_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    low = settings.story.words_per_scene_min.for_language(story.language)
    high = settings.story.words_per_scene_max.for_language(story.language)
    return [
        f"scene {index + 1} has {count} words; use between {low:g} and {high:g}"
        for index, scene in enumerate(story.scenes)
        if not low <= (count := word_count(scene.narration)) <= high
    ]


def configured_duration(settings: KidsStorySettings, language: str) -> tuple[int, int]:  # noqa: ARG001
    return settings.story.target_duration_seconds, settings.story.duration_tolerance_seconds


def duration_problems(
    story: Story, settings: KidsStorySettings, duration: DurationTarget = configured_duration
) -> list[str]:
    rate = settings.story.words_per_minute.for_language(story.language)
    seconds = estimated_seconds(story, rate)
    target, tolerance = duration(settings, story.language)
    if abs(seconds - target) <= tolerance:
        return []
    return [f"the story reads in about {seconds:.0f} s; aim for {target} s (within {tolerance} s)"]


def ending_text(story: Story, scenes: int) -> str:
    return " ".join(scene.narration for scene in story.scenes[-scenes:])


def closing_scenes(count: int) -> str:
    return "the last scene" if count == 1 else f"the last {count} scenes"


def ending_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    problems = []
    style = settings.story.ending_style
    count = settings.story.ending_scenes
    ending = ending_text(story, count)
    if says_moral(style) and not contains_phrase(ending, story.moral):
        problems.append(f"say the moral, word for word, in {closing_scenes(count)}")
    refrain = settings.series.refrain.for_language(story.language)
    if says_refrain(style) and refrain and not contains_phrase(ending, refrain):
        problems.append(f'say the refrain "{refrain}" in {closing_scenes(count)}')
    return problems


def moral_problems(story: Story, settings: KidsStorySettings) -> list[str]:  # noqa: ARG001
    return [] if story.moral.strip() else ['write the moral in "moral"']


def all_text(story: Story) -> str:
    parts = [story.title, story.moral, story.hook_line, *story.questions]
    scenes = [
        text for scene in story.scenes for text in (scene.narration, scene.action, *scene.texts)
    ]
    return " ".join([*parts, *scenes])


def listed_phrases(text: str, phrases: list[str]) -> list[str]:
    return [phrase for phrase in phrases if contains_phrase(text, phrase)]


def banned_word_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    found = listed_phrases(all_text(story), settings.safety.banned_words)
    return [f"remove these words: {', '.join(found)}"] if found else []


def brand_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    found = listed_phrases(all_text(story), settings.safety.brand_names)
    return [f"remove these brand names: {', '.join(found)}"] if found else []


def framing_lines(story: Story, settings: KidsStorySettings) -> list[str]:
    series = settings.series
    return [line.for_language(story.language) for line in (series.intro_line, series.outro_line)]


def child_term_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    if settings.safety.for_kids:
        return []
    checked = {
        "the audience is general": [all_text(story)],
        "the series intro or outro line must change in the settings": framing_lines(
            story, settings
        ),
    }
    return [
        f"{reason}: {child_term_message(found)}"
        for reason, texts in checked.items()
        if (found := child_terms_in_any(texts))
    ]


def reading_level_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    if not settings.safety.for_kids:
        return []
    rules = settings.story
    metrics = reading_metrics(
        narration_of(story), rules.long_word_graphemes.for_language(story.language)
    )
    problems = []
    limit = rules.max_average_sentence_words.for_language(story.language)
    if metrics.average_sentence_words > limit:
        problems.append(f"use shorter sentences: at most {limit:g} words on average")
    if metrics.long_word_share > rules.max_long_word_share:
        problems.append("use fewer long words")
    return problems


def cast_problems(story: Story, settings: KidsStorySettings, seed: str = "") -> list[str]:
    known = {member.id for member in episode_cast(settings, seed)}
    unknown = sorted(set(story.character_ids) - known)
    return [f"only use cast ids; unknown: {', '.join(unknown)}"] if unknown else []


CheckedGate = tuple[StoryCheck | None, Gate]
MORAL_GATE: CheckedGate = (None, moral_problems)
SAFETY_GATES: tuple[CheckedGate, ...] = (
    (None, banned_word_problems),
    (None, brand_problems),
    (None, child_term_problems),
)
READING_GATES: tuple[CheckedGate, ...] = ((StoryCheck.READING_LEVEL, reading_level_problems),)


def switched_on(check: StoryCheck | None, settings: KidsStorySettings) -> bool:
    return check is None or check in settings.story.enabled_checks


def problems_of(
    gates: tuple[CheckedGate, ...], story: Story, settings: KidsStorySettings
) -> list[str]:
    return [
        problem
        for check, gate in gates
        if switched_on(check, settings)
        for problem in gate(story, settings)
    ]
