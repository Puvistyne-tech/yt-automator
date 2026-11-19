from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.series import BANNED_WORDS
from autotube.pipelines.narrated_video.settings.story_audience import ReadingLevel
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck
from autotube.pipelines.narrated_video.story.checks import story_problems
from tests.fixtures.builtin_catalog import BUILTIN_IDS
from tests.fixtures.explainer_data import explainer_settings, explainer_story
from tests.fixtures.template_records import template
from tests.fixtures.template_settings import GENERAL, KIDS

ENGINE = NarratedVideoEngine()
BUILTINS = {item.id: item for item in ENGINE.builtin_templates()}
KIDS_LEVELS = {ReadingLevel.TODDLER, ReadingLevel.PRESCHOOL, ReadingLevel.EARLY_READER}
GENERAL_IDS = [key for key in BUILTIN_IDS if BUILTINS[key].audience is GENERAL]
KIDS_IDS = [key for key in BUILTIN_IDS if BUILTINS[key].audience is KIDS]
RELAXED = "scary_stories"


def settings_of(item: PipelineTemplate) -> KidsStorySettings:
    settings = ENGINE.pipeline(item).settings_model()
    assert isinstance(settings, KidsStorySettings)
    return settings


def with_dead(audience: TemplateAudience) -> list[str]:
    script = explainer_story()
    last = script.scenes[-1]
    scenes = [*script.scenes[:-1], last.model_copy(update={"narration": f"{last.narration} dead"})]
    return story_problems(
        script.model_copy(update={"scenes": scenes}), explainer_settings(audience)
    )


@pytest.mark.parametrize("template_id", GENERAL_IDS)
def test_a_general_builtin_carries_no_kids_safety_defaults(template_id: str) -> None:
    settings = settings_of(BUILTINS[template_id])
    assert not set(BANNED_WORDS) <= set(settings.safety.banned_words)
    assert (settings.story.age_min, settings.story.age_max) != (3, 7)
    assert settings.story.reading_level is ReadingLevel.GENERAL
    assert StoryCheck.READING_LEVEL not in settings.story.enabled_checks


@pytest.mark.parametrize("template_id", sorted(set(GENERAL_IDS) - {RELAXED}))
def test_a_general_builtin_starts_with_an_empty_banned_word_list(template_id: str) -> None:
    assert settings_of(BUILTINS[template_id]).safety.banned_words == []


@pytest.mark.parametrize("template_id", [*KIDS_IDS, f"{RELAXED}@kids"])
def test_a_kids_template_keeps_the_whole_kids_floor(template_id: str) -> None:
    base, _, kids = template_id.partition("@")
    item = BUILTINS[base]
    chosen = template(audience=KIDS, definition=item.definition) if kids else item
    settings = settings_of(chosen)
    assert set(BANNED_WORDS) <= set(settings.safety.banned_words)
    assert settings.story.age_max <= 12 and settings.story.reading_level in KIDS_LEVELS
    assert StoryCheck.READING_LEVEL in settings.story.enabled_checks


def test_dead_passes_a_general_explainer_and_fails_a_kids_one() -> None:
    assert with_dead(GENERAL) == []
    assert "remove these words: dead" in with_dead(KIDS)


@pytest.mark.parametrize(
    "story", [{"age_max": 13}, {"reading_level": "general"}], ids=["age", "reading_level"]
)
def test_kids_settings_refuse_general_ages_and_reading_level(story: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="kids"):
        KidsStorySettings.model_validate({"story": story})
    general = {"safety": {"audience": "general"}, "story": story}
    assert KidsStorySettings.model_validate(general).safety.for_kids is False
