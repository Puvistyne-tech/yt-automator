from __future__ import annotations

from pydantic import JsonValue

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.ui_basic import BASIC_KEY
from autotube.domain.ui_hidden import HIDDEN_KEY
from autotube.domain.ui_paths import listed_paths
from autotube.pipelines.narrated_video.resources import resource_object
from autotube.pipelines.narrated_video.settings.base import LocalizedText
from autotube.pipelines.narrated_video.structures.registry import structure_spec
from autotube.pipelines.narrated_video.template.audience import audience_hidden_paths
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.structure_pins import structure_hidden_paths

DEFINITION_UI_FILE = "definition.json"
DESCRIPTION_ROWS = 10


def per_language_text_area(rows: int) -> JsonObject:
    area: JsonObject = {"ui:widget": "textarea", "ui:options": {"rows": rows}}
    return dict.fromkeys(LocalizedText.model_fields, area)


def definition_ui_schema() -> JsonObject:
    layout = resource_object("ui", DEFINITION_UI_FILE)
    return {**layout, "description_template": per_language_text_area(DESCRIPTION_ROWS)}


def derived_hidden(
    engine_ui: JsonObject, definition: NarratedDefinition, audience: TemplateAudience
) -> list[JsonValue]:
    fixed = [
        *listed_paths(engine_ui.get(HIDDEN_KEY)),
        *audience_hidden_paths(audience),
        *structure_hidden_paths(definition.structure),
    ]
    kept = {*definition.hidden, *structure_spec(definition.structure).shown_paths}
    return [*definition.hidden, *(path for path in dict.fromkeys(fixed) if path not in kept)]


def derived_basic(engine_ui: JsonObject, definition: NarratedDefinition) -> JsonValue:
    if definition.basic:
        return list(definition.basic)
    spec = structure_spec(definition.structure)
    base = list(spec.basic_paths) or listed_paths(engine_ui.get(BASIC_KEY))
    kept = [path for path in base if path not in spec.hidden_paths]
    return [*kept, *(path for path in spec.shown_paths if path not in kept)]


def derived_ui_schema(
    engine_ui: JsonObject, definition: NarratedDefinition, audience: TemplateAudience
) -> JsonObject:
    return {
        **engine_ui,
        BASIC_KEY: derived_basic(engine_ui, definition),
        HIDDEN_KEY: derived_hidden(engine_ui, definition, audience),
    }
