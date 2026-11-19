from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_descriptors import default_settings_of, settings_schema_of
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.publishing.templates import (
    METADATA_PLACEHOLDERS,
    template_values,
)
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in
from autotube.pipelines.narrated_video.template.audience import audience_defaults, with_audience
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.merging import deep_merged
from autotube.pipelines.narrated_video.template.settings_model import (
    kids_settings_model,
    settings_model_for,
)
from autotube.pipelines.narrated_video.template.text_leaves import text_leaves
from tests.fixtures.kids_data import story
from tests.fixtures.prompt_pins import stored_settings

KIDS, GENERAL = TemplateAudience.KIDS, TemplateAudience.GENERAL
ENGINE = KidsStorySettings().model_dump(mode="json")


def defaults_for(audience: TemplateAudience = KIDS, **definition: Any) -> dict[str, Any]:
    model = settings_model_for(NarratedDefinition.model_validate(definition), audience)
    return default_settings_of(model)


def changed_paths(before: Any, after: Any, prefix: str = "") -> set[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        return {
            path
            for key in before.keys() | after.keys()
            for path in changed_paths(before.get(key), after.get(key), f"{prefix}{key}.")
        }
    return set() if before == after else {prefix.rstrip(".")}


def test_an_empty_kids_definition_keeps_every_engine_default() -> None:
    assert defaults_for() == ENGINE
    assert settings_schema_of(settings_model_for(NarratedDefinition(), KIDS)) == (
        settings_schema_of(KidsStorySettings)
    )


def test_the_kids_model_validates_stored_settings_unchanged() -> None:
    loaded = kids_settings_model().model_validate(stored_settings())
    assert loaded.model_dump() == KidsStorySettings().model_dump()
    assert issubclass(kids_settings_model(), KidsStorySettings)


def test_a_definition_changes_exactly_the_defaults_it_names() -> None:
    changed = defaults_for(
        visual_style="anime",
        tone="dry and witty",
        topics=["volcanoes", " ", "tides"],
        title_template={"en": "{title}!"},
        short_title_template={"ta": "{title} #Shorts!"},
        description_template={"en": "{title} by {series}"},
        tags={"en": ["science"]},
        hashtags={"ta": ["#அறிவியல்"]},
        music_mood="bright synth",
    )
    assert changed_paths(ENGINE, changed) == {
        "look.visual_style",
        "story.tone",
        "story.themes",
        "metadata.title_template.en",
        "metadata.short_title_template.ta",
        "metadata.description_template.en",
        "metadata.tags.en",
        "metadata.hashtags.ta",
        "music.mood_prompt",
    }
    assert changed["story"]["themes"] == ["volcanoes", "tides"]
    assert changed["metadata"]["title_template"]["ta"] == ENGINE["metadata"]["title_template"]["ta"]


@pytest.mark.parametrize(
    ("length", "seconds", "scenes"), [("short", 60, (4, 6)), ("long", 300, (14, 18))]
)
def test_length_presets_set_duration_and_scene_counts(
    length: str, seconds: int, scenes: tuple[int, int]
) -> None:
    rules = defaults_for(length=length)["story"]
    assert rules["target_duration_seconds"] == seconds
    assert (rules["scene_count_min"], rules["scene_count_max"]) == scenes
    assert defaults_for(length="standard") == ENGINE


def test_the_brief_and_category_reach_the_settings() -> None:
    changed = defaults_for(brief="  Odd facts about space.  ", category="27")
    assert changed["story"]["extra_instructions"] == "Every video is about: Odd facts about space."
    assert changed["metadata"]["category"] == "27"


def test_the_overlay_wins_over_the_mapped_definition_and_merges_deeply() -> None:
    changed = defaults_for(
        tone="calm",
        settings={"story": {"tone": "lively", "scene_count_max": 12}, "voice": {}},
    )
    assert changed["story"]["tone"] == "lively"
    assert changed["story"]["scene_count_max"] == 12
    assert changed["story"]["scene_count_min"] == ENGINE["story"]["scene_count_min"]


def test_deep_merge_replaces_lists_and_scalars_and_merges_objects() -> None:
    merged = deep_merged({"a": {"b": 1, "c": [1]}, "d": 1}, {"a": {"c": [2]}, "d": {"e": 1}})
    assert merged == {"a": {"b": 1, "c": [2]}, "d": {"e": 1}}


def test_a_blank_general_template_inherits_no_child_directed_text() -> None:
    general = defaults_for(GENERAL)
    assert [text for text in text_leaves(general) if child_terms_in(text)] == []
    expected = deep_merged(ENGINE, audience_defaults(GENERAL))
    pinned = deep_merged(expected, {"safety": {"audience": "general"}})
    assert general == KidsStorySettings.model_validate(pinned).model_dump(mode="json")


def test_general_defaults_replace_the_childrens_story_frame() -> None:
    general = defaults_for(GENERAL)
    assert [member["species"] for member in general["cast"]] == ["woman"]
    assert general["story"]["ending_style"] == "open"
    assert general["series"]["refrain"] == {"en": "", "ta": ""}
    assert general["look"]["visual_style"] != ENGINE["look"]["visual_style"]
    assert general["story"]["themes"] != ENGINE["story"]["themes"]
    assert general["story"]["tone"] != ENGINE["story"]["tone"]
    assert general["visuals"]["motion_prompt"] != ENGINE["visuals"]["motion_prompt"]


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_the_derived_model_pins_the_template_audience(audience: TemplateAudience) -> None:
    model = settings_model_for(NarratedDefinition(), audience)
    other = GENERAL if audience is KIDS else KIDS
    assert model.model_validate({"safety": {"audience": other.value}}).safety.audience is audience
    assert model.model_validate(KidsStorySettings()).safety.audience is audience
    assert model().safety.audience is audience


def no_default(section: str) -> object:
    return {"section": section}


def test_pinning_leaves_input_it_cannot_read_to_validation() -> None:
    assert with_audience("nonsense", KIDS, no_default) == "nonsense"
    assert with_audience({"safety": 3}, KIDS, no_default) == {"safety": 3}


def test_metadata_placeholders_match_the_filled_values() -> None:
    assert set(template_values(story(), KidsStorySettings())) == set(METADATA_PLACEHOLDERS)


def test_derived_models_are_built_once_per_definition_and_audience() -> None:
    first = settings_model_for(NarratedDefinition(tone="dry"), GENERAL)
    assert settings_model_for(NarratedDefinition(tone="dry"), GENERAL) is first
    assert settings_model_for(NarratedDefinition(tone="dry"), KIDS) is not first
    assert settings_model_for(NarratedDefinition(tone="wet"), GENERAL) is not first
    assert kids_settings_model() is kids_settings_model()
