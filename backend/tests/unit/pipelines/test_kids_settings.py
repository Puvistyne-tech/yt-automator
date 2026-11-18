from __future__ import annotations

from typing import Any, cast

import pytest
from pydantic import ValidationError

from automator.domain.model_base import JsonObject
from automator.domain.pipeline_descriptors import Aspect
from automator.domain.ui_schema import ui_schema_problems
from automator.domain.validation import validated_settings
from automator.pipelines.kids_story.plugin import KidsStoryPipeline
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.settings.subtitles import SubtitleSettings

SCHEMA = KidsStorySettings.model_json_schema()


def untitled_fields(schema: dict[str, Any]) -> list[str]:
    models = {"root": schema, **schema.get("$defs", {})}
    return [
        f"{model}.{name}"
        for model, definition in models.items()
        for name, field in definition.get("properties", {}).items()
        if not field.get("title") or not field.get("description")
    ]


def section_fields(name: str) -> set[str]:
    reference = SCHEMA["properties"][name]
    target = reference.get("$ref") or reference.get("items", {}).get("$ref", "")
    return set(SCHEMA["$defs"][target.rsplit("/", 1)[-1]]["properties"])


def test_every_settings_field_has_a_title_and_description() -> None:
    assert untitled_fields(SCHEMA) == []


def test_section_references_carry_their_own_title_and_description() -> None:
    for name, field in SCHEMA["properties"].items():
        assert field.get("title") and field.get("description"), name


def test_empty_settings_equal_the_defaults_for_every_language() -> None:
    empty, defaults = KidsStorySettings.model_validate({}), KidsStorySettings()
    for code in ("en", "ta"):
        assert empty.series.name.for_language(code) == defaults.series.name.for_language(code)
        assert empty.thumbnail.font_files.for_language(code) == (
            defaults.thumbnail.font_files.for_language(code)
        )
    assert empty == defaults


def test_ui_schema_follows_the_ui_schema_contract() -> None:
    descriptor = KidsStoryPipeline().descriptor
    assert ui_schema_problems(descriptor.ui_schema, descriptor.settings_schema) == []


def test_ui_orders_list_every_field_of_their_section() -> None:
    ui = KidsStoryPipeline().descriptor.ui_schema
    for section in ("series", "story", "short"):
        node = ui[section]
        assert isinstance(node, dict) and set(cast(list[str], node["ui:order"])) == (
            section_fields(section)
        ), section
    cast_items = cast(dict[str, Any], ui["cast"])["items"]
    assert set(cast_items["ui:order"]) == section_fields("cast")


def test_settings_helpers_resolve_sizes_and_characters() -> None:
    settings = KidsStorySettings()
    assert settings.video_size("episode") == (1920, 1080)
    assert settings.video_size("short") == (1080, 1920)
    assert [member.id for member in settings.characters(["mittu", "nobody", "raju"])] == [
        "mittu",
        "raju",
    ]


def test_default_settings_validate_and_round_trip() -> None:
    descriptor = KidsStoryPipeline().descriptor
    settings = KidsStorySettings.model_validate(descriptor.default_settings)
    assert settings == KidsStorySettings()
    assert settings.cast[0].id == "raju" and settings.cast[0].species == "baby elephant"
    assert 3 <= len(settings.cast) <= 4


def test_descriptor_declares_languages_variants_and_kids_content() -> None:
    descriptor = KidsStoryPipeline().descriptor
    assert descriptor.type_id == "kids_story" and descriptor.name == "Kids story videos"
    assert descriptor.makes_kids_content
    assert descriptor.language_codes == {"en", "ta"}
    aspects = {variant.id: variant.aspect for variant in descriptor.variants}
    assert aspects == {"episode": Aspect.LANDSCAPE, "short": Aspect.PORTRAIT}
    assert descriptor.stage_ids == (
        "story",
        "voice",
        "art",
        "motion",
        "music",
        "assemble",
        "package",
    )


def test_ui_schema_sections_cover_every_settings_section() -> None:
    ui = KidsStoryPipeline().descriptor.ui_schema
    sections = cast(list[dict[str, Any]], ui["ui:sections"])
    assert [section["title"] for section in sections][:2] == ["Series", "Story"]
    covered = [name for section in sections for name in section["fields"]]
    assert sorted(covered) == sorted(KidsStorySettings.model_fields)
    assert cast(dict[str, Any], ui["music"])["volume"] == {
        "ui:widget": "range",
        "ui:options": {"step": 0.01},
    }


@pytest.mark.parametrize(
    "settings",
    [
        {"story": {"scene_count_min": 9, "scene_count_max": 8}},
        {"story": {"age_min": 8, "age_max": 4}},
        {"music": {"volume": 2}},
        {"subtitles": {"primary_color": "white"}},
        {"cast": []},
        {"unknown": 1},
        {"visuals": {"badge_corner": "center"}},
        {"thumbnail": {"text_position": "top_left"}},
        {"thumbnail": {"max_bytes": 3_000_000}},
        {"story": {"ending_scenes": 0}},
        {"quality": {"subtitle_overlap_penalty": 2}},
    ],
)
def test_invalid_settings_are_rejected(settings: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        KidsStorySettings.model_validate(settings)


def test_duplicate_character_ids_are_rejected() -> None:
    member = KidsStorySettings().cast[0].model_dump()
    with pytest.raises(ValidationError):
        KidsStorySettings.model_validate({"cast": [member, member]})


def test_settings_saved_with_the_old_pixel_margins_still_load() -> None:
    stored = {"subtitles": {"margin_bottom": 90, "short_margin_bottom": 320, "max_lines": 3}}
    loaded = KidsStorySettings.model_validate(stored).subtitles
    assert loaded.max_lines == 3
    assert loaded.bottom_margin_share == SubtitleSettings().bottom_margin_share


@pytest.mark.parametrize("family", ["Fonts & Co.", "Kid's Font", ""])
def test_unsafe_subtitle_font_names_are_rejected_with_a_field_error(family: str) -> None:
    stored: JsonObject = {"subtitles": {"font_family": {"en": "Noto Sans", "ta": family}}}
    errors = validated_settings(KidsStorySettings, stored)[1]
    assert list(errors) == ["settings.subtitles.font_family"]
