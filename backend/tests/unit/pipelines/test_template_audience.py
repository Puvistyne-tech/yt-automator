from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_descriptors import (
    KIDS_CONTENT,
    PipelineDescriptor,
)
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.series import (
    BANNED_WORDS,
    BRAND_NAMES,
    NO_HARM_RULE,
    PICTURE_EXCLUSIONS,
    SafetySettings,
)
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck
from autotube.pipelines.narrated_video.template.kids_floor import (
    audience_floor,
    kids_floor,
    listed_terms,
)
from autotube.pipelines.narrated_video.template.settings_model import kids_settings_model
from tests.fixtures.template_settings import defaults_for, model_for, pipeline_of

KIDS, GENERAL = TemplateAudience.KIDS, TemplateAudience.GENERAL
ENGINE = KidsStorySettings().model_dump(mode="json")
ENGINE_HIDDEN = [
    "safety.audience",
    "story.structure",
    "story.preview_attempts",
    "story.item_count",
    "story.quiz_questions",
    "story.answer_choices",
]
WEAKENED = {
    "series": {"editorial_rules": ["Be fun."]},
    "safety": {"banned_words": [], "brand_names": ["Acme"], "picture_exclusions": "blur"},
}


def descriptor_of(audience: TemplateAudience, **definition: Any) -> PipelineDescriptor:
    return pipeline_of(audience, **definition).descriptor


def floors_of(defaults: dict[str, Any]) -> tuple[Any, ...]:
    safety = defaults["safety"]
    return (
        defaults["series"]["editorial_rules"],
        safety["banned_words"],
        safety["brand_names"],
        safety["picture_exclusions"],
    )


def test_only_kids_templates_carry_the_kids_capability() -> None:
    assert descriptor_of(KIDS).capabilities == (KIDS_CONTENT,)
    assert descriptor_of(GENERAL).capabilities == ()
    assert descriptor_of(GENERAL).makes_kids_content is False


def test_the_derived_ui_schema_hides_the_audience_and_general_age_fields() -> None:
    own = KidsStoryPipeline().descriptor.ui_schema
    kids, general = descriptor_of(KIDS).ui_schema, descriptor_of(GENERAL).ui_schema
    assert kids == own and own["ui:hidden"] == ENGINE_HIDDEN
    assert general["ui:hidden"] == [
        *ENGINE_HIDDEN,
        "story.age_min",
        "story.age_max",
        "story.reading_level",
        "story.source",
    ]
    assert general["ui:basic"] == own["ui:basic"]


def test_the_definition_sets_basic_and_adds_hidden_paths() -> None:
    ui = descriptor_of(GENERAL, basic=["story.tone"], hidden=["story.morals"]).ui_schema
    assert ui["ui:basic"] == ["story.tone"]
    assert ui["ui:hidden"] == [
        "story.morals",
        *ENGINE_HIDDEN,
        "story.age_min",
        "story.age_max",
        "story.reading_level",
        "story.source",
    ]


def test_a_kids_overlay_cannot_remove_any_floor() -> None:
    defaults = defaults_for(KIDS, settings=WEAKENED)
    safety, rules = defaults["safety"], defaults["series"]["editorial_rules"]
    assert rules == ["Be fun.", NO_HARM_RULE]
    assert safety["banned_words"] == BANNED_WORDS
    assert safety["brand_names"] == ["Acme", *BRAND_NAMES]
    assert listed_terms(safety["picture_exclusions"]) == ["blur", *listed_terms(PICTURE_EXCLUSIONS)]
    assert safety["audience"] == "kids"


def test_a_general_overlay_is_not_floored() -> None:
    defaults = defaults_for(GENERAL, settings=WEAKENED)
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


def test_no_mapped_definition_field_touches_a_kids_floor() -> None:
    mapped = defaults_for(
        KIDS,
        brief="Animal friends.",
        length="long",
        tone="cosy",
        topics=["rain"],
        visual_style="ink_line_art",
        music_mood="soft harp",
        title_template={"en": "{title}!"},
        tags={"en": ["stories"]},
        hashtags={"en": ["#Stories"]},
        category="27",
    )
    assert floors_of(mapped) == floors_of(ENGINE)


def test_a_partial_overlay_gets_the_floor_without_duplicates() -> None:
    safety = {"banned_words": ["kill", "Gun"], "brand_names": ["lego", "Acme"]}
    floored = defaults_for(KIDS, settings={"safety": safety})["safety"]
    assert floored["banned_words"] == [
        "kill",
        "Gun",
        *(w for w in BANNED_WORDS if w not in ("kill", "gun")),
    ]
    assert floored["brand_names"] == ["lego", "Acme", *(b for b in BRAND_NAMES if b != "Lego")]


EMPTIED = {
    "safety": {"banned_words": [], "brand_names": [], "picture_exclusions": ""},
    "story": {"enabled_checks": []},
}


@pytest.mark.parametrize("model", [kids_settings_model(), model_for(KIDS, tone="cosy")])
def test_kids_automations_cannot_empty_the_floors(model: type[KidsStorySettings]) -> None:
    loaded = model.model_validate(EMPTIED)
    assert loaded.safety.banned_words == BANNED_WORDS
    assert loaded.safety.brand_names == BRAND_NAMES
    assert listed_terms(loaded.safety.picture_exclusions) == listed_terms(PICTURE_EXCLUSIONS)
    assert loaded.story.enabled_checks == [StoryCheck.READING_LEVEL]
    as_models = model.model_validate({"safety": SafetySettings(banned_words=["Kill"])})
    assert as_models.safety.banned_words[0] == "Kill"
    assert "kill" not in as_models.safety.banned_words


def test_general_automations_are_not_floored() -> None:
    loaded = model_for(GENERAL).model_validate(EMPTIED)
    assert loaded.safety.banned_words == [] and loaded.story.enabled_checks == []


def test_the_audience_floor_leaves_other_input_alone() -> None:
    assert audience_floor("raw", KIDS) == "raw"
    assert audience_floor({"safety": {"banned_words": []}}, GENERAL) == {
        "safety": {"banned_words": []}
    }
