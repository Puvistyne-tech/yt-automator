from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs
from autotube.pipelines.narrated_video.scoring.score import score_items
from autotube.pipelines.narrated_video.settings.story import StorySource
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck, Structure
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.model import StoryText, with_text
from autotube.pipelines.narrated_video.structures.explainer import HIDDEN_PATHS
from autotube.pipelines.narrated_video.template.settings_model import kids_settings_model
from tests.fixtures.explainer_data import (
    EXPLAINER,
    explainer_pipeline,
    explainer_settings,
    explainer_story,
    explainer_text_ta,
)
from tests.fixtures.kids_data import story
from tests.fixtures.template_settings import GENERAL, KIDS

AUDIENCES = [KIDS, GENERAL]
HOOKLESS = (
    "Sunlight is really many colours mixed together, and every single drop of rain in the sky "
    "splits those colours apart for us to see."
)


@pytest.mark.parametrize("audience", AUDIENCES)
def test_an_explainer_model_pins_its_structure_and_the_writer_source(
    audience: TemplateAudience,
) -> None:
    loaded = explainer_settings(audience, story={"structure": "story", "source": "bundled_only"})
    assert loaded.story.structure is Structure.EXPLAINER
    assert loaded.story.source is StorySource.LLM_WITH_FALLBACK
    assert loaded.cast == []


def test_the_kids_story_model_pins_the_story_structure() -> None:
    loaded = kids_settings_model().model_validate({"story": {"structure": "explainer"}})
    assert loaded.story.structure is Structure.STORY


@pytest.mark.parametrize("audience", AUDIENCES)
def test_a_written_explainer_passes_its_checks(audience: TemplateAudience) -> None:
    settings = explainer_settings(audience)
    assert story_problems(explainer_story(), settings) == []
    translated = with_text(explainer_story(), StoryText.model_validate(explainer_text_ta()), "ta")
    assert translation_problems(translated, settings) == []


def test_the_explainer_needs_a_hook_and_the_takeaway_and_skips_cast_and_ending() -> None:
    settings = explainer_settings(KIDS)
    scenes = explainer_story().scenes
    broken = [scenes[0].model_copy(update={"narration": HOOKLESS}), *scenes[1:-1], scenes[1]]
    loose = explainer_story(scenes=broken)
    expected = [
        "open the first scene with the question this video answers",
        "say the takeaway, word for word, in the last scene",
    ]
    assert story_problems(loose, settings) == expected
    assert translation_problems(loose, settings) == expected
    switched = settings.story.model_copy(update={"enabled_checks": [StoryCheck.SCENE_COUNT]})
    assert story_problems(loose, settings.model_copy(update={"story": switched})) == []
    assert story_problems(story(), settings) == expected[:1]


def score_ids(audience: TemplateAudience, structure: dict[str, str]) -> set[str]:
    settings = explainer_settings(audience) if structure else kids_settings_model()()
    sample = explainer_story() if structure else story()
    inputs = ScoreInputs(settings, ("en",), (), Path(), {"en": sample}, {}, None)
    return {item.id for item in score_items(inputs)}


def test_explainer_scoring_swaps_story_items_for_the_structure_item() -> None:
    explainer = score_ids(GENERAL, EXPLAINER)
    assert "structure" in explainer
    assert not {"moral_and_refrain", "character_consistency"} & explainer
    assert "structure" not in score_ids(KIDS, {})


@pytest.mark.parametrize("audience", AUDIENCES)
def test_the_explainer_hides_cast_and_story_only_settings(audience: TemplateAudience) -> None:
    descriptor = explainer_pipeline(audience).descriptor
    hidden = descriptor.ui_schema["ui:hidden"]
    assert isinstance(hidden, list) and {*HIDDEN_PATHS, "story.source"} <= set(hidden)
    assert descriptor.default_settings["cast"] == []
