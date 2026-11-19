from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_descriptors import KIDS_CONTENT, default_settings_of
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline
from autotube.pipelines.narrated_video.settings.series import (
    BANNED_WORDS,
    BRAND_NAMES,
    NO_HARM_RULE,
    PICTURE_EXCLUSIONS,
)
from autotube.pipelines.narrated_video.template.kids_floor import kids_floor, listed_terms
from tests.fixtures.template_records import template

KIDS, GENERAL = TemplateAudience.KIDS, TemplateAudience.GENERAL
WEAKENED = {
    "series": {"editorial_rules": ["Be fun."]},
    "safety": {"banned_words": [], "brand_names": ["Acme"], "picture_exclusions": "blur"},
}


def descriptor_of(audience: TemplateAudience, **definition: Any) -> Any:
    pipeline = NarratedVideoEngine().pipeline(template(audience=audience, definition=definition))
    return pipeline.descriptor


def defaults_of(audience: TemplateAudience, **definition: Any) -> dict[str, Any]:
    pipeline = NarratedVideoEngine().pipeline(template(audience=audience, definition=definition))
    return default_settings_of(pipeline.settings_model)


def test_only_kids_templates_carry_the_kids_capability() -> None:
    assert descriptor_of(KIDS).capabilities == (KIDS_CONTENT,)
    assert descriptor_of(GENERAL).capabilities == ()
    assert descriptor_of(GENERAL).makes_kids_content is False


def test_the_derived_ui_schema_hides_the_audience_and_general_age_fields() -> None:
    own = KidsStoryPipeline().descriptor.ui_schema
    kids, general = descriptor_of(KIDS).ui_schema, descriptor_of(GENERAL).ui_schema
    assert kids == own and own["ui:hidden"] == ["safety.audience"]
    assert general["ui:hidden"] == [
        "safety.audience",
        "story.age_min",
        "story.age_max",
        "story.reading_level",
        "story.source",
    ]
    assert general["ui:basic"] == own["ui:basic"]


def test_the_definition_sets_basic_and_adds_hidden_paths() -> None:
    ui = descriptor_of(GENERAL, basic=["story.tone"], hidden=["story.morals"]).ui_schema
    assert ui["ui:basic"] == ["story.tone"]
    assert ui["ui:hidden"][:2] == ["story.morals", "safety.audience"]


def test_a_kids_overlay_cannot_remove_any_floor() -> None:
    defaults = defaults_of(KIDS, settings=WEAKENED)
    safety, rules = defaults["safety"], defaults["series"]["editorial_rules"]
    assert rules == ["Be fun.", NO_HARM_RULE]
    assert safety["banned_words"] == BANNED_WORDS
    assert safety["brand_names"] == ["Acme", *BRAND_NAMES]
    assert listed_terms(safety["picture_exclusions"]) == ["blur", *listed_terms(PICTURE_EXCLUSIONS)]
    assert safety["audience"] == "kids"


def test_a_general_overlay_is_not_floored() -> None:
    defaults = defaults_of(GENERAL, settings=WEAKENED)
    assert defaults["safety"]["banned_words"] == []
    assert defaults["safety"]["picture_exclusions"] == "blur"


def test_the_floor_keeps_text_that_already_meets_it() -> None:
    floored = kids_floor({"safety": {"picture_exclusions": PICTURE_EXCLUSIONS.upper()}})
    assert floored == {"safety": {"picture_exclusions": PICTURE_EXCLUSIONS.upper()}}


@pytest.mark.parametrize(
    "values",
    [
        {"safety": "loose"},
        {"series": {}},
        {"safety": {"banned_words": "kill", "picture_exclusions": 3}},
    ],
)
def test_the_floor_leaves_unreadable_values_to_validation(values: dict[str, Any]) -> None:
    assert kids_floor(values) == values
