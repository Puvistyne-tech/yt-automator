from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from automator.domain.pipeline_descriptors import Aspect
from automator.pipelines.kids_story.plugin import KidsStoryPipeline
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.registry import build_pipeline_registry


def untitled_fields(schema: dict[str, Any]) -> list[str]:
    models = {"root": schema, **schema.get("$defs", {})}
    return [
        f"{model}.{name}"
        for model, definition in models.items()
        for name, field in definition.get("properties", {}).items()
        if not field.get("title") or not field.get("description")
    ]


def test_every_settings_field_has_a_title_and_description() -> None:
    assert untitled_fields(KidsStorySettings.model_json_schema()) == []


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
    ],
)
def test_invalid_settings_are_rejected(settings: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        KidsStorySettings.model_validate(settings)


def test_duplicate_character_ids_are_rejected() -> None:
    member = KidsStorySettings().cast[0].model_dump()
    with pytest.raises(ValidationError):
        KidsStorySettings.model_validate({"cast": [member, member]})


def test_registry_builds_kids_story() -> None:
    registry = build_pipeline_registry()
    assert [pipeline.descriptor.type_id for pipeline in registry.list()] == ["kids_story"]
    assert registry.get("kids_story") is not None and registry.get("missing") is None
