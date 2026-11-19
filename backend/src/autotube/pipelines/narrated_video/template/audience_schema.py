from __future__ import annotations

from typing import Any

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.story_audience import ReadingLevel

READING_LEVEL_FIELD = "reading_level"
ADULT_LEVELS = frozenset({ReadingLevel.GENERAL.value})


def kids_levels(field: dict[str, Any]) -> dict[str, Any]:
    if "oneOf" not in field:
        return field
    choices = [choice for choice in field["oneOf"] if choice.get("const") not in ADULT_LEVELS]
    return {**field, "oneOf": choices}


def kids_definition(definition: dict[str, Any]) -> dict[str, Any]:
    properties = definition.get("properties", {})
    if READING_LEVEL_FIELD not in properties:
        return definition
    narrowed = kids_levels(properties[READING_LEVEL_FIELD])
    return {**definition, "properties": {**properties, READING_LEVEL_FIELD: narrowed}}


def audience_schema(schema: dict[str, Any], audience: TemplateAudience) -> dict[str, Any]:
    if audience is not TemplateAudience.KIDS or "$defs" not in schema:
        return schema
    definitions = {name: kids_definition(item) for name, item in schema["$defs"].items()}
    return {**schema, "$defs": definitions}
