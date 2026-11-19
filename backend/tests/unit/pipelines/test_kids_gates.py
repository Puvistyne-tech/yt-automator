from __future__ import annotations

from typing import Any

import pytest

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.ending_gate import ending_problems
from autotube.pipelines.narrated_video.story.gates import (
    Gate,
    banned_word_problems,
    brand_problems,
    cast_problems,
    duration_problems,
    reading_level_problems,
    scene_count_problems,
    words_per_scene_problems,
)
from autotube.pipelines.narrated_video.story.model import Story
from tests.fixtures.kids_data import quick_settings, story

SETTINGS = KidsStorySettings()
SIXTY_WORDS = " ".join(["Kavin walked on."] * 20)
LAST = "Kavin felt warm and bright inside and smiled at all of his dear friends today."
MORAL_ONLY = f"{LAST} Sharing makes everyone happier."
REFRAIN_ONLY = f"{LAST} Be kind, be brave, be you!"


def with_narration(index: int, text: str, base: Story | None = None) -> Story:
    good = base or story()
    scenes = list(good.scenes)
    scenes[index] = scenes[index].model_copy(update={"narration": text})
    return good.model_copy(update={"scenes": scenes})


def with_cast(*names: str) -> Story:
    scenes = [scene.model_copy(update={"characters": list(names)}) for scene in story().scenes]
    return story().model_copy(update={"scenes": scenes})


CASES: list[tuple[Gate, Story, dict[str, Any], list[str]]] = [
    (
        scene_count_problems,
        story(),
        {"story": {"scene_count_min": 10, "scene_count_max": 12}},
        ["use between 10 and 12 scenes, not 9"],
    ),
    (
        scene_count_problems,
        story(),
        {"story": {"scene_count_max": 8}},
        ["use exactly 8 scenes, not 9"],
    ),
    (
        words_per_scene_problems,
        with_narration(2, "Kavin smiled."),
        {},
        ["scene 3 has 2 words; use between 18 and 50"],
    ),
    (
        words_per_scene_problems,
        with_narration(2, SIXTY_WORDS),
        {},
        ["scene 3 has 60 words; use between 18 and 50"],
    ),
    (
        ending_problems,
        with_narration(8, LAST),
        {},
        [
            "say the moral, word for word, in the last 2 scenes",
            'say the refrain "Be kind, be brave, be you!" in the last 2 scenes',
        ],
    ),
    (
        ending_problems,
        with_narration(8, REFRAIN_ONLY),
        {},
        ["say the moral, word for word, in the last 2 scenes"],
    ),
    (
        ending_problems,
        with_narration(8, MORAL_ONLY),
        {},
        ['say the refrain "Be kind, be brave, be you!" in the last 2 scenes'],
    ),
    (
        ending_problems,
        with_narration(8, MORAL_ONLY),
        {"series": {"refrain": {"en": "", "ta": ""}}},
        [],
    ),
    (
        ending_problems,
        with_narration(7, MORAL_ONLY, with_narration(8, REFRAIN_ONLY)),
        {"story": {"ending_scenes": 1}},
        ["say the moral, word for word, in the last scene"],
    ),
    (ending_problems, with_narration(7, MORAL_ONLY, with_narration(8, REFRAIN_ONLY)), {}, []),
    (
        banned_word_problems,
        story(hook_line="Where is the knife?"),
        {},
        ["remove these words: knife"],
    ),
    (banned_word_problems, story(questions=["Who has a gun?"]), {}, ["remove these words: gun"]),
    (
        banned_word_problems,
        with_narration(1, f"{LAST} blood kill"),
        {},
        ["remove these words: kill, blood"],
    ),
    (
        brand_problems,
        story(title="Kavin and the Lego Mango"),
        {},
        ["remove these brand names: Lego"],
    ),
    (
        reading_level_problems,
        story(),
        {"story": {"max_average_sentence_words": {"en": 4, "ta": 4}}},
        ["use shorter sentences: at most 4 words on average"],
    ),
    (
        reading_level_problems,
        story(),
        {"story": {"long_word_graphemes": {"en": 6, "ta": 6}, "max_long_word_share": 0.0}},
        ["use fewer long words"],
    ),
    (
        cast_problems,
        with_cast("kavin", "zebra", "dragon"),
        {},
        ["only use cast ids; unknown: dragon, zebra"],
    ),
]


@pytest.mark.parametrize(("gate", "draft", "sections", "expected"), CASES)
def test_gates(gate: Gate, draft: Story, sections: dict[str, Any], expected: list[str]) -> None:
    assert gate(draft, quick_settings(**sections)) == expected


def test_a_good_story_passes_every_gate() -> None:
    assert story_problems(story(), SETTINGS) == []


def test_duration_gate_on_both_sides_and_per_language() -> None:
    long = quick_settings(story={"target_duration_seconds": 60, "duration_tolerance_seconds": 5})
    assert duration_problems(story(), long)[0].startswith(
        "the story is too long: 258 words, use at most 130"
    )
    assert "aim for 60 s (within 5 s)" in duration_problems(story(), long)[0]
    short = quick_settings(story={"target_duration_seconds": 600, "duration_tolerance_seconds": 5})
    assert "aim for 600 s" in duration_problems(story(), short)[0]
    assert "too short: 258 words, need at least 1190" in duration_problems(story(), short)[0]
    slow_tamil = quick_settings(story={"words_per_minute": {"en": 120, "ta": 10}})
    assert duration_problems(story("ta"), slow_tamil) != []
    assert duration_problems(story("en"), slow_tamil) == []


def test_story_problems_combine_every_gate_in_order() -> None:
    bad = with_narration(8, "monster Pepsi", with_cast("dragon"))
    settings = quick_settings(story={"scene_count_min": 10, "scene_count_max": 12})
    problems = story_problems(bad, settings)
    expected_starts = [
        "use between 10 and 12 scenes",
        "scene 9 has 2 words",
        "say the moral",
        "say the refrain",
        "only use cast ids; unknown: dragon",
        "remove these words: monster",
        "remove these brand names: Pepsi",
    ]
    found = iter(problems)
    assert all(any(item.startswith(start) for item in found) for start in expected_starts)


def test_translation_problems_cover_ending_and_safety_only() -> None:
    bad = with_narration(8, "monster Pepsi", with_cast("dragon"))
    assert translation_problems(bad, SETTINGS) == [
        "say the moral, word for word, in the last 2 scenes",
        'say the refrain "Be kind, be brave, be you!" in the last 2 scenes',
        "remove these words: monster",
        "remove these brand names: Pepsi",
    ]
