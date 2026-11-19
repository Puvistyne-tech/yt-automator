from __future__ import annotations

from typing import Any

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.story_audience import ReadingLevel
from autotube.pipelines.narrated_video.template.audience_schema import audience_schema
from autotube.pipelines.narrated_video.template.settings_model import pinned_settings_model


def offered_levels(schema: dict[str, Any]) -> set[str]:
    return {
        choice["const"]
        for definition in schema["$defs"].values()
        for name, field in definition.get("properties", {}).items()
        if name == "reading_level"
        for choice in field.get("oneOf", [])
    }


def score_weight(schema: dict[str, Any]) -> dict[str, Any]:
    weight: dict[str, Any] = schema["$defs"]["ScoreWeights"]["properties"]["reading_level"]
    return weight


def test_a_kids_form_never_offers_the_general_reading_level() -> None:
    schema = pinned_settings_model(TemplateAudience.KIDS).model_json_schema()
    assert offered_levels(schema) == {level.value for level in ReadingLevel} - {"general"}
    assert score_weight(schema)["type"] == "number" and "oneOf" not in score_weight(schema)


def test_a_general_form_keeps_every_reading_level() -> None:
    schema = pinned_settings_model(TemplateAudience.GENERAL).model_json_schema()
    assert offered_levels(schema) == {level.value for level in ReadingLevel}


def test_a_schema_without_definitions_is_left_alone() -> None:
    assert audience_schema({"type": "object"}, TemplateAudience.KIDS) == {"type": "object"}
