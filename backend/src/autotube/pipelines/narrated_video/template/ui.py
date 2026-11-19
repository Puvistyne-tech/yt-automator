from __future__ import annotations

from pydantic import JsonValue

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.ui_basic import BASIC_KEY
from autotube.domain.ui_hidden import HIDDEN_KEY
from autotube.domain.ui_paths import listed_paths
from autotube.pipelines.narrated_video.template.audience import audience_hidden_paths
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition


def derived_hidden(
    engine_ui: JsonObject, definition: NarratedDefinition, audience: TemplateAudience
) -> list[JsonValue]:
    fixed = [*listed_paths(engine_ui.get(HIDDEN_KEY)), *audience_hidden_paths(audience)]
    return [
        *definition.hidden,
        *(path for path in dict.fromkeys(fixed) if path not in definition.hidden),
    ]


def derived_basic(engine_ui: JsonObject, definition: NarratedDefinition) -> JsonValue:
    if definition.basic:
        return list(definition.basic)
    return engine_ui.get(BASIC_KEY, [])


def derived_ui_schema(
    engine_ui: JsonObject, definition: NarratedDefinition, audience: TemplateAudience
) -> JsonObject:
    return {
        **engine_ui,
        BASIC_KEY: derived_basic(engine_ui, definition),
        HIDDEN_KEY: derived_hidden(engine_ui, definition, audience),
    }
