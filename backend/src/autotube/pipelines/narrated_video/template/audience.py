from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, TypeAdapter

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.resources import resource_json
from autotube.pipelines.narrated_video.settings.story import StorySource

AUDIENCE_PATH = "safety.audience"
SOURCE_PATH = "story.source"
GENERAL_HIDDEN_PATHS = ("story.age_min", "story.age_max", "story.reading_level", SOURCE_PATH)
JSON_OBJECT = TypeAdapter(JsonObject)
SectionDefault = Callable[[str], object]
Pins = dict[str, dict[str, str]]


def audience_defaults(audience: TemplateAudience) -> JsonObject:
    if audience is TemplateAudience.KIDS:
        return {}
    return JSON_OBJECT.validate_python(resource_json("template", "general_defaults.json"))


def audience_hidden_paths(audience: TemplateAudience) -> tuple[str, ...]:
    if audience is TemplateAudience.KIDS:
        return (AUDIENCE_PATH,)
    return (AUDIENCE_PATH, *GENERAL_HIDDEN_PATHS)


def audience_pins(audience: TemplateAudience) -> Pins:
    pins: Pins = {"safety": {"audience": audience.value}}
    if audience is TemplateAudience.GENERAL:
        pins["story"] = {"source": StorySource.LLM_WITH_FALLBACK.value}
    return pins


def plain(value: object) -> object:
    return value.model_dump(mode="json") if isinstance(value, BaseModel) else value


def pinned_section(
    values: dict[str, object], section: str, pins: dict[str, str], default: SectionDefault
) -> dict[str, object] | None:
    current = plain(values[section] if section in values else default(section))
    return {**current, **pins} if isinstance(current, dict) else None


def with_audience(data: object, audience: TemplateAudience, default: SectionDefault) -> object:
    return with_pins(data, audience_pins(audience), default)


def with_pins(data: object, all_pins: Pins, default: SectionDefault) -> object:
    values = plain(data)
    if not isinstance(values, dict):
        return data
    pinned = dict(values)
    for section, pins in all_pins.items():
        section_values = pinned_section(values, section, pins, default)
        if section_values is None:
            return data
        pinned[section] = section_values
    return pinned
