from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.publishing.templates import template_values
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.checks import story_problems, translation_problems
from autotube.pipelines.narrated_video.story.prompts import story_request
from autotube.pipelines.narrated_video.structures.registry import structure_spec
from tests.fixtures.list_data import list_settings, list_story, tamil_list
from tests.fixtures.template_settings import GENERAL, KIDS, defaults_for

COUNTDOWN = "countdown"
DESCENDING = "number the items from 7 down to 1, so the last item is number 1"


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_a_written_countdown_and_its_translation_pass_their_checks(
    audience: TemplateAudience,
) -> None:
    settings = list_settings(audience, COUNTDOWN)
    assert settings.story.structure is Structure.COUNTDOWN
    assert story_problems(list_story(countdown=True), settings) == []
    tamil = tamil_list(countdown=True)
    assert translation_problems(tamil, settings) == []
    assert tamil.scenes[-2].number == 1


def test_a_countdown_must_end_on_number_one() -> None:
    settings = list_settings(KIDS, COUNTDOWN)
    assert story_problems(list_story(), settings) == [DESCENDING]
    assert translation_problems(tamil_list(), settings) == [DESCENDING]
    assert story_problems(list_story(countdown=True), list_settings(KIDS)) == [
        "number the items from 1 up to 7, in that order"
    ]


def test_the_countdown_prompt_counts_down_and_shares_the_list_shape() -> None:
    request = story_request(list_settings(GENERAL, COUNTDOWN), "the fastest animals", "en")
    assert "numbered from 7 down to 1, so the last item is number 1" in request.prompt
    assert "Shape of the countdown script:" in request.prompt
    assert "short countdown videos" in (request.system or "")
    spec, plain = structure_spec(Structure.COUNTDOWN), structure_spec(Structure.LIST)
    assert spec.title == "Countdown" and spec.placeholders == plain.placeholders
    assert spec.hidden_paths == plain.hidden_paths


def test_a_countdown_lists_its_items_in_video_order() -> None:
    values = template_values(list_story(countdown=True), list_settings(GENERAL, COUNTDOWN))
    assert values["count"] == "7"
    assert values["items"].startswith("Honey keeps for years, Wings beat very fast, ")


def test_a_countdown_template_uses_its_own_defaults() -> None:
    defaults = defaults_for(GENERAL, structure=COUNTDOWN)
    assert defaults["cast"] == [] and defaults["story"]["structure"] == COUNTDOWN
    assert "{count}" in defaults["metadata"]["description_template"]["en"]
