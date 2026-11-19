from __future__ import annotations

from pydantic import JsonValue

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience
from autotube.domain.validation import field_path
from autotube.pipelines.narrated_video.story.child_terms import (
    child_term_message,
    child_terms_in_any,
)
from autotube.pipelines.narrated_video.styles.library import style_named
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.text_leaves import text_leaves

DEFINITION_TEXT_FIELDS = (
    "brief",
    "tone",
    "topics",
    "music_mood",
    "title_template",
    "short_title_template",
    "description_template",
    "tags",
    "hashtags",
)
UNSCREENED_SECTIONS = frozenset({"safety"})
STYLE_SECTION, STYLE_FIELD = "look", "visual_style"
SETTINGS_PREFIX = "definition.settings"


def style_texts(style_id: JsonValue) -> list[str]:
    style = style_named(style_id) if isinstance(style_id, str) else None
    return [] if style is None else text_leaves(style.model_dump(mode="json"))


def definition_texts(definition: NarratedDefinition) -> dict[str, list[str]]:
    values = definition.model_dump(mode="json")
    texts = {f"definition.{field}": text_leaves(values[field]) for field in DEFINITION_TEXT_FIELDS}
    return texts | {"definition.visual_style": style_texts(definition.visual_style)}


def section_texts(section: str, value: JsonValue) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {field_path(SETTINGS_PREFIX, section): text_leaves(value)}
    texts = {
        field_path(SETTINGS_PREFIX, section, key): text_leaves(item) for key, item in value.items()
    }
    if section == STYLE_SECTION:
        path = field_path(SETTINGS_PREFIX, section, STYLE_FIELD)
        texts[path] = [*texts.get(path, []), *style_texts(value.get(STYLE_FIELD))]
    return texts


def overlay_texts(overlay: JsonObject) -> dict[str, list[str]]:
    return {
        path: texts
        for section, value in overlay.items()
        if section not in UNSCREENED_SECTIONS
        for path, texts in section_texts(section, value).items()
    }


def child_term_problems(
    template: PipelineTemplate, definition: NarratedDefinition
) -> dict[str, str]:
    if template.audience is TemplateAudience.KIDS:
        return {}
    screened = {
        "name": [template.name],
        **definition_texts(definition),
        **overlay_texts(definition.settings),
    }
    return {
        path: child_term_message(found)
        for path, texts in screened.items()
        if (found := child_terms_in_any(texts))
    }
