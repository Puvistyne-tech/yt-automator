from __future__ import annotations

from typing import Any

import pytest

from autotube.pipelines.kids_story.settings.story_choices import StoryCheck
from autotube.pipelines.kids_story.story.gates import story_problems, translation_problems
from autotube.pipelines.kids_story.story.model import Story
from tests.fixtures.kids_data import quick_settings, story

LAST = "Kavin felt warm and bright inside and smiled at all of his dear friends today."
UNSAFE = f"{LAST} Disney gave him a knife."
SAFETY_PROBLEMS = ["remove these words: knife", "remove these brand names: Disney"]


def ending_with(text: str) -> Story:
    scenes = list(story().scenes)
    scenes[-1] = scenes[-1].model_copy(update={"narration": text})
    return story().model_copy(update={"scenes": scenes})


def all_but(check: StoryCheck) -> list[StoryCheck]:
    return [kept for kept in StoryCheck if kept is not check]


BROKEN_RULES: list[tuple[StoryCheck, dict[str, Any]]] = [
    (StoryCheck.SCENE_COUNT, {"scene_count_min": 10, "scene_count_max": 12}),
    (StoryCheck.WORDS_PER_SCENE, {"words_per_scene_max": {"en": 10, "ta": 10}}),
    (StoryCheck.DURATION, {"target_duration_seconds": 600, "duration_tolerance_seconds": 0}),
    (StoryCheck.READING_LEVEL, {"max_average_sentence_words": {"en": 4, "ta": 4}}),
    (StoryCheck.CAST, {"cast_per_episode": 1}),
]


@pytest.mark.parametrize(("check", "rule"), BROKEN_RULES, ids=[c.value for c, _ in BROKEN_RULES])
def test_each_optional_check_switches_off_only_its_own_gate(
    check: StoryCheck, rule: dict[str, Any]
) -> None:
    assert story_problems(story(), quick_settings(story=rule)) != []
    switched_off = quick_settings(story={**rule, "enabled_checks": all_but(check)})
    assert story_problems(story(), switched_off) == []


def test_switched_off_checks_do_not_run_but_child_safety_always_does() -> None:
    broken = ending_with(UNSAFE)
    broken = broken.model_copy(update={"scenes": broken.scenes[-3:]})
    settings = quick_settings(story={"enabled_checks": []})
    assert story_problems(broken, settings) == SAFETY_PROBLEMS
    assert len(story_problems(broken, quick_settings())) > len(SAFETY_PROBLEMS)


def test_translations_keep_child_safety_checks_with_every_check_off() -> None:
    settings = quick_settings(story={"enabled_checks": []})
    assert translation_problems(ending_with(UNSAFE), settings) == SAFETY_PROBLEMS


def test_switching_off_the_ending_check_also_skips_it_for_translations() -> None:
    no_ending = ending_with(LAST)
    kept = all_but(StoryCheck.ENDING)
    assert translation_problems(no_ending, quick_settings(story={"enabled_checks": kept})) == []
    assert translation_problems(no_ending, quick_settings()) != []


def test_child_safety_checks_cannot_be_listed() -> None:
    assert {check.value for check in StoryCheck}.isdisjoint({"banned_words", "brand_names"})
    with pytest.raises(ValueError, match="enabled_checks"):
        quick_settings(story={"enabled_checks": ["banned_words"]})
