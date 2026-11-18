from __future__ import annotations

from collections.abc import Callable

from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.story.reading import (
    estimated_seconds,
    narration_of,
    reading_metrics,
)
from automator.pipelines.kids_story.story.words import contains_phrase, word_count

Gate = Callable[[Story, KidsStorySettings], list[str]]


def scene_count_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    low, high = settings.story.scene_count_min, settings.story.scene_count_max
    if low <= len(story.scenes) <= high:
        return []
    return [f"use between {low} and {high} scenes, not {len(story.scenes)}"]


def words_per_scene_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    low = settings.story.words_per_scene_min.for_language(story.language)
    high = settings.story.words_per_scene_max.for_language(story.language)
    return [
        f"scene {index + 1} has {count} words; use between {low:g} and {high:g}"
        for index, scene in enumerate(story.scenes)
        if not low <= (count := word_count(scene.narration)) <= high
    ]


def duration_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    rate = settings.story.words_per_minute.for_language(story.language)
    seconds = estimated_seconds(story, rate)
    target = settings.story.target_duration_seconds
    tolerance = settings.story.duration_tolerance_seconds
    if abs(seconds - target) <= tolerance:
        return []
    return [f"the story reads in about {seconds:.0f} s; aim for {target} s (within {tolerance} s)"]


def ending_text(story: Story, scenes: int) -> str:
    return " ".join(scene.narration for scene in story.scenes[-scenes:])


def closing_scenes(count: int) -> str:
    return "the last scene" if count == 1 else f"the last {count} scenes"


def ending_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    problems = []
    count = settings.story.ending_scenes
    ending = ending_text(story, count)
    if not contains_phrase(ending, story.moral):
        problems.append(f"say the moral, word for word, in {closing_scenes(count)}")
    refrain = settings.series.refrain.for_language(story.language)
    if refrain and not contains_phrase(ending, refrain):
        problems.append(f'say the refrain "{refrain}" in {closing_scenes(count)}')
    return problems


def all_text(story: Story) -> str:
    parts = [story.title, story.moral, story.hook_line, *story.questions]
    return " ".join([*parts, *(scene.narration for scene in story.scenes)])


def listed_phrases(text: str, phrases: list[str]) -> list[str]:
    return [phrase for phrase in phrases if contains_phrase(text, phrase)]


def banned_word_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    found = listed_phrases(all_text(story), settings.safety.banned_words)
    return [f"remove these words: {', '.join(found)}"] if found else []


def brand_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    found = listed_phrases(all_text(story), settings.safety.brand_names)
    return [f"remove these brand names: {', '.join(found)}"] if found else []


def reading_level_problems(story: Story, settings: KidsStorySettings) -> list[str]:
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


def cast_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    known = {member.id for member in settings.cast}
    unknown = sorted(set(story.character_ids) - known)
    return [f"only use cast ids; unknown: {', '.join(unknown)}"] if unknown else []


GATES: tuple[Gate, ...] = (
    scene_count_problems,
    words_per_scene_problems,
    duration_problems,
    ending_problems,
    banned_word_problems,
    brand_problems,
    reading_level_problems,
    cast_problems,
)


TRANSLATION_GATES: tuple[Gate, ...] = (ending_problems, banned_word_problems, brand_problems)


def problems_of(gates: tuple[Gate, ...], story: Story, settings: KidsStorySettings) -> list[str]:
    return [problem for gate in gates for problem in gate(story, settings)]


def story_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    return problems_of(GATES, story, settings)


def translation_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    return problems_of(TRANSLATION_GATES, story, settings)
