from __future__ import annotations

from functools import cache

from autotube.domain.json_schema import Schema
from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience
from autotube.domain.ui_basic import basic_problems
from autotube.domain.ui_hidden import hidden_problems
from autotube.domain.validation import validated_settings
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.styles.library import style_ids
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.length_problems import length_problems
from autotube.pipelines.narrated_video.template.placeholder_problems import placeholder_problems
from autotube.pipelines.narrated_video.template.settings_model import (
    pinned_settings_model,
    template_defaults,
)
from autotube.pipelines.narrated_video.template.term_screen import (
    SETTINGS_PREFIX,
    child_term_problems,
)
from autotube.pipelines.narrated_video.template.ui import derived_ui_schema

DEFINITION = "definition"


def joined(problems: list[str]) -> str:
    return "; ".join(problems)


def style_problems(definition: NarratedDefinition) -> dict[str, str]:
    style = definition.visual_style
    if not style or style in style_ids():
        return {}
    return {"definition.visual_style": f"unknown visual style {style!r}"}


@cache
def engine_settings_schema() -> Schema:
    return KidsStorySettings.model_json_schema()


def ui_problems(
    definition: NarratedDefinition, audience: TemplateAudience, engine_ui: JsonObject
) -> dict[str, str]:
    schema = engine_settings_schema()
    ui = derived_ui_schema(engine_ui, definition, audience)
    found = {
        "definition.basic": basic_problems(ui, schema),
        "definition.hidden": hidden_problems(ui, schema),
    }
    return {path: joined(problems) for path, problems in found.items() if problems}


def settings_problems(template: PipelineTemplate, definition: NarratedDefinition) -> dict[str, str]:
    model = pinned_settings_model(template.audience, definition.structure)
    defaults = template_defaults(definition, template.audience)
    _, errors = validated_settings(model, defaults, SETTINGS_PREFIX)
    return errors


def template_problems(template: PipelineTemplate, engine_ui: JsonObject) -> dict[str, str]:
    definition, errors = validated_settings(NarratedDefinition, template.definition, DEFINITION)
    if not isinstance(definition, NarratedDefinition):
        return errors
    styled = style_problems(definition)
    lengthy = {} if styled else length_problems(definition, template.audience)
    checked = {
        **styled,
        **placeholder_problems(definition),
        **ui_problems(definition, template.audience, engine_ui),
        **child_term_problems(template, definition),
        **lengthy,
    }
    if styled or lengthy:
        return checked
    return {**checked, **settings_problems(template, definition)}
