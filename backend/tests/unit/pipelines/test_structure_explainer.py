from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.story import StorySource
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck, Structure
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.structures.registry import structure_spec
from autotube.pipelines.narrated_video.template.settings_model import kids_settings_model
from tests.fixtures.explainer_data import (
    NARRATIONS_TA,
    TAKEAWAY_ENDING,
    explainer_pipeline,
    explainer_settings,
    explainer_story,
    tamil_explainer,
    without_hook_or_takeaway,
)
from tests.fixtures.kids_data import story
from tests.fixtures.template_settings import GENERAL, KIDS

AUDIENCES = [KIDS, GENERAL]


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
    assert translation_problems(tamil_explainer(), settings) == []


def test_the_explainer_needs_a_hook_and_the_takeaway_and_skips_cast_and_ending() -> None:
    settings = explainer_settings(KIDS)
    loose = without_hook_or_takeaway()
    expected = [
        "open the first scene with the question this video answers",
        "say the takeaway, word for word, in the last scene",
    ]
    assert story_problems(loose, settings) == expected
    assert translation_problems(loose, settings) == expected
    switched = settings.story.model_copy(update={"enabled_checks": [StoryCheck.SCENE_COUNT]})
    assert story_problems(loose, settings.model_copy(update={"story": switched})) == []
    assert story_problems(story(), settings) == expected[:1]


def test_a_tamil_translation_needs_the_hook_and_the_takeaway() -> None:
    settings = explainer_settings(GENERAL, story=TAKEAWAY_ENDING)
    narrations = list(NARRATIONS_TA)
    hookless = [narrations[1], *narrations[1:-1], narrations[1]]
    assert translation_problems(tamil_explainer(hookless), settings) == [
        "open the first scene with the question this video answers",
        "say the takeaway, word for word, in the last scene",
    ]
    full_width = [narrations[1].replace(".", "？", 1), *narrations[1:]]
    assert translation_problems(tamil_explainer(full_width), settings) == []


@pytest.mark.parametrize("audience", AUDIENCES)
def test_the_explainer_hides_cast_and_story_only_settings(audience: TemplateAudience) -> None:
    descriptor = explainer_pipeline(audience).descriptor
    hidden = descriptor.ui_schema["ui:hidden"]
    spec = structure_spec(Structure.EXPLAINER)
    assert isinstance(hidden, list) and {*spec.hidden_paths, "story.source"} - set(
        spec.shown_paths
    ) <= set(hidden)
    assert "story.ending_style" not in hidden
    assert descriptor.default_settings["cast"] == []
