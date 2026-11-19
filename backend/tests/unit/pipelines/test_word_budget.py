from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.gates import duration_problems
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompts import story_request
from autotube.pipelines.narrated_video.story.reading import word_range
from autotube.pipelines.narrated_video.structures.length import duration_target, scene_range
from autotube.pipelines.narrated_video.structures.word_budget import (
    WordBudget,
    per_scene_words,
    word_budget,
)
from tests.fixtures.builtin_catalog import BUILTIN_IDS
from tests.fixtures.kids_data import quick_settings, story
from tests.fixtures.template_settings import GENERAL, model_for

ENGINE = NarratedVideoEngine()
BUILTINS = {item.id: item for item in ENGINE.builtin_templates()}
MAC_STORY = {
    "target_duration_seconds": 60,
    "duration_tolerance_seconds": 20,
    "scene_count_min": 4,
    "scene_count_max": 6,
}
LANGUAGES = ["en", "ta"]


def builtin_settings(template_id: str) -> KidsStorySettings:
    settings = ENGINE.pipeline(BUILTINS[template_id]).settings_model()
    assert isinstance(settings, KidsStorySettings)
    return settings


def even_story(language: str, scenes: int, words: int) -> Story:
    narration = " ".join(["word"] * words)
    return story(language).model_copy(
        update={"scenes": [story().scenes[0].model_copy(update={"narration": narration})] * scenes}
    )


def test_word_range_rounds_inwards() -> None:
    assert word_range(40, 80, 120) == (80, 160)
    assert word_range(40, 80, 80) == (54, 106)
    assert word_range(-5, 10, 60) == (0, 10)


def test_the_mac_story_budget_fits_the_duration_gate() -> None:
    budget = word_budget(quick_settings(story=MAC_STORY), "en")
    assert budget == WordBudget(total=(80, 160), target=120, per_scene=(20, 26))
    prompt = story_request(quick_settings(story=MAC_STORY), "sharing", "en").prompt
    assert "between 20 and 26 words, written in English" in prompt
    assert "between 80 and 160 words in total, about 120" in prompt


def test_the_long_explainer_budget_reaches_its_window() -> None:
    settings = model_for(GENERAL, structure="explainer", length="long")()
    assert word_budget(settings, "en") == WordBudget((510, 690), 600, (37, 38))
    assert "aim for 300 s" in duration_problems(even_story("en", 14, 13), settings)[0]
    assert (
        "too short: 182 words, need at least 510"
        in duration_problems(even_story("en", 14, 13), settings)[0]
    )


@pytest.mark.parametrize(
    ("total", "scenes", "configured", "expected"),
    [
        ((80, 160), (4, 6), (18, 50), (20, 26)),
        ((80, 160), (2, 10), (18, 50), (18, 50)),
        ((80, 160), (2, 10), (8, 12), (8, 12)),
        ((80, 160), (2, 10), (30, 50), (30, 50)),
        ((10, 20), (2, 4), (40, 50), (40, 50)),
    ],
    ids=["every-count", "some-count", "some-count-clipped", "configured-tail", "configured"],
)
def test_per_scene_words_narrow_only_as_far_as_they_can(
    total: tuple[int, int],
    scenes: tuple[int, int],
    configured: tuple[int, int],
    expected: tuple[int, int],
) -> None:
    assert per_scene_words(total, scenes, configured) == expected


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("template_id", BUILTIN_IDS)
def test_any_story_inside_a_builtin_budget_passes_the_duration_gate(
    template_id: str, language: str
) -> None:
    settings = builtin_settings(template_id)
    budget = word_budget(settings, language)
    fewest, most = scene_range(settings)
    target, tolerance = duration_target(settings, language)
    assert target - tolerance > 0
    for scenes, words in ((fewest, budget.per_scene[0]), (most, budget.per_scene[1])):
        sample = even_story(language, scenes, words)
        assert duration_problems(sample, settings, duration=duration_target) == []


def test_a_length_the_scenes_cannot_reach_is_refused() -> None:
    tight = {
        "story": {
            "scene_count_min": 4,
            "scene_count_max": 6,
            "words_per_scene_max": {"en": 20, "ta": 40},
        }
    }
    with pytest.raises(ValidationError, match="change the scene count, the words per scene"):
        model_for(GENERAL, structure="explainer", length="long").model_validate(tight)
    found = ENGINE.problems(
        BUILTINS["history_in_five_minutes"].model_copy(
            update={
                "definition": {**BUILTINS["history_in_five_minutes"].definition, "settings": tight}
            }
        )
    )
    assert "4 to 6 scenes read in 36 to 60 s in English" in " ".join(found.values())
