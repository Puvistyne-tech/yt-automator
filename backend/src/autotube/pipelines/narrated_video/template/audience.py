from __future__ import annotations

from pydantic import BaseModel, TypeAdapter

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.resources import resource_json

AUDIENCE_PATH = "safety.audience"
GENERAL_HIDDEN_PATHS = ("story.age_min", "story.age_max", "story.reading_level")
JSON_OBJECT = TypeAdapter(JsonObject)


def audience_defaults(audience: TemplateAudience) -> JsonObject:
    if audience is TemplateAudience.KIDS:
        return {}
    return JSON_OBJECT.validate_python(resource_json("template", "general_defaults.json"))


def audience_hidden_paths(audience: TemplateAudience) -> tuple[str, ...]:
    if audience is TemplateAudience.KIDS:
        return (AUDIENCE_PATH,)
    return (AUDIENCE_PATH, *GENERAL_HIDDEN_PATHS)


def plain(value: object) -> object:
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else value


def with_audience(data: object, audience: TemplateAudience, safety_default: object) -> object:
    values = plain(data)
    if not isinstance(values, dict):
        return data
    safety = plain(values.get("safety", safety_default))
    if not isinstance(safety, dict):
        return data
    return {**values, "safety": {**safety, "audience": audience.value}}
