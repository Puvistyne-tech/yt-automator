from __future__ import annotations

from pydantic import JsonValue

from autotube.domain.json_text import text_leaves
from autotube.domain.validation import field_path
from autotube.pipelines.narrated_video.settings.placeholders import unknown_placeholder_message
from autotube.pipelines.narrated_video.structures.registry import metadata_placeholders
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition

DEFINITION_TEMPLATES = ("title_template", "short_title_template", "description_template")
OVERLAY_TEMPLATES = (*DEFINITION_TEMPLATES, "playlist_title")
OVERLAY_SECTION = "metadata"


def definition_templates(definition: NarratedDefinition) -> dict[str, list[str]]:
    values = definition.model_dump(mode="json")
    return {
        field_path("definition", field): text_leaves(values[field])
        for field in DEFINITION_TEMPLATES
    }


def overlay_templates(definition: NarratedDefinition) -> dict[str, list[str]]:
    section: JsonValue = definition.settings.get(OVERLAY_SECTION)
    if not isinstance(section, dict):
        return {}
    return {
        field_path("definition", "settings", OVERLAY_SECTION, field): text_leaves(section[field])
        for field in OVERLAY_TEMPLATES
        if field in section
    }


def placeholder_problems(definition: NarratedDefinition) -> dict[str, str]:
    allowed = metadata_placeholders(definition.structure)
    written = {**definition_templates(definition), **overlay_templates(definition)}
    return {
        path: message
        for path, texts in written.items()
        if (message := unknown_placeholder_message(path.rsplit(".", 1)[-1], texts, allowed))
    }
