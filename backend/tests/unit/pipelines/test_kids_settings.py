from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from automator.domain.pipeline_descriptors import Aspect
from automator.pipelines.kids_story.plugin import KidsStoryPipeline
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.registry import installed_pipelines

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


def test_ui_order_and_widgets_name_real_fields() -> None:
    ui = KidsStoryPipeline().descriptor.ui_schema
    order, widgets = ui["order"], ui["widgets"]
    assert isinstance(order, dict) and isinstance(widgets, dict)
    for section, names in order.items():
        assert isinstance(names, list) and set(names) == section_fields(section), section
    for path in widgets:
        section, field = path.split(".")[:2]
        assert field in section_fields(section), path


def test_settings_helpers_resolve_sizes_and_characters() -> None:
    settings = KidsStorySettings()
    assert settings.video_size("episode") == (1920, 1080)
    assert settings.video_size("short") == (1080, 1920)
    assert [member.id for member in settings.characters(["mittu", "nobody", "kutty"])] == [
        "mittu",
        "kutty",
    ]


def test_default_settings_validate_and_round_trip() -> None:
    descriptor = KidsStoryPipeline().descriptor
    settings = KidsStorySettings.model_validate(descriptor.default_settings)
    assert settings == KidsStorySettings()
    assert settings.cast[0].id == "kutty" and settings.cast[0].species == "baby elephant"
    assert 3 <= len(settings.cast) <= 4


def test_descriptor_declares_languages_variants_and_kids_content() -> None:
    descriptor = KidsStoryPipeline().descriptor
    assert descriptor.type_id == "kids_story" and descriptor.name == "Kutty Stories"
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
    descriptor = KidsStoryPipeline().descriptor
    sections = descriptor.ui_schema["sections"]
    assert isinstance(sections, list)
    covered: set[str] = set()
    for section in sections:
        assert isinstance(section, dict) and isinstance(section["fields"], list)
        covered.update(str(name) for name in section["fields"])
    assert covered == set(KidsStorySettings.model_fields)
    widgets = descriptor.ui_schema["widgets"]
    assert isinstance(widgets, dict) and widgets["music.volume"] == {
        "widget": "slider",
        "step": 0.01,
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


def test_installed_pipelines_include_kids_story() -> None:
    assert [pipeline.descriptor.type_id for pipeline in installed_pipelines()] == ["kids_story"]
