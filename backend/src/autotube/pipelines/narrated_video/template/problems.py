from __future__ import annotations

from autotube.domain.json_schema import Schema
from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience
from autotube.domain.ui_basic import basic_problems
from autotube.domain.ui_hidden import hidden_problems
from autotube.domain.validation import validated_settings
from autotube.pipelines.narrated_video.publishing.templates import METADATA_PLACEHOLDERS
from autotube.pipelines.narrated_video.settings.base import LocalizedText
from autotube.pipelines.narrated_video.settings.placeholders import checked_template
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.child_terms import child_term_message, child_terms_in
from autotube.pipelines.narrated_video.styles.library import style_ids
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.settings_model import (
    pinned_settings_model,
    template_defaults,
)
from autotube.pipelines.narrated_video.template.ui import derived_ui_schema

DEFINITION = "definition"
SETTINGS_PREFIX = "definition.settings"


def joined(problems: list[str]) -> str:
    return "; ".join(problems)


def style_problems(definition: NarratedDefinition) -> dict[str, str]:
    style = definition.visual_style
    if not style or style in style_ids():
        return {}
    return {"definition.visual_style": f"unknown visual style {style!r}"}


def placeholder_problem(field: str, value: LocalizedText) -> dict[str, str]:
    try:
        checked_template(field, value, METADATA_PLACEHOLDERS)
    except ValueError as error:
        return {f"{DEFINITION}.{field}": str(error)}
    return {}


def placeholder_problems(definition: NarratedDefinition) -> dict[str, str]:
    templates = {
        "title_template": definition.title_template,
        "short_title_template": definition.short_title_template,
        "description_template": definition.description_template,
    }
    return {
        path: message
        for field, value in templates.items()
        for path, message in placeholder_problem(field, value).items()
    }


def ui_problems(
    definition: NarratedDefinition, audience: TemplateAudience, engine_ui: JsonObject
) -> dict[str, str]:
    schema: Schema = KidsStorySettings.model_json_schema()
    ui = derived_ui_schema(engine_ui, definition, audience)
    found = {
        "definition.basic": basic_problems(ui, schema),
        "definition.hidden": hidden_problems(ui, schema),
    }
    return {path: joined(problems) for path, problems in found.items() if problems}


def localized_texts(*values: LocalizedText) -> list[str]:
    return [text for value in values for text in value.model_dump().values()]


def screened_texts(template: PipelineTemplate, settings: KidsStorySettings) -> dict[str, list[str]]:
    metadata, series = settings.metadata, settings.series
    return {
        "name": [template.name],
        "definition.brief": [str(template.definition.get("brief", ""))],
        "definition.tags": [*metadata.tags.en, *metadata.tags.ta],
        "definition.hashtags": [*metadata.hashtags.en, *metadata.hashtags.ta],
        f"{SETTINGS_PREFIX}.series": localized_texts(
            series.name, series.tagline, series.refrain, series.intro_line, series.outro_line
        ),
    }


def found_terms(texts: list[str]) -> list[str]:
    return list(dict.fromkeys(term for text in texts for term in child_terms_in(text)))


def child_term_problems(template: PipelineTemplate, settings: KidsStorySettings) -> dict[str, str]:
    if template.audience is TemplateAudience.KIDS:
        return {}
    return {
        path: child_term_message(found)
        for path, texts in screened_texts(template, settings).items()
        if (found := found_terms(texts))
    }


def settings_problems(template: PipelineTemplate, definition: NarratedDefinition) -> dict[str, str]:
    model = pinned_settings_model(template.audience)
    defaults = template_defaults(definition, template.audience)
    settings, errors = validated_settings(model, defaults, SETTINGS_PREFIX)
    if not isinstance(settings, KidsStorySettings):
        return errors
    return child_term_problems(template, settings)


def template_problems(template: PipelineTemplate, engine_ui: JsonObject) -> dict[str, str]:
    definition, errors = validated_settings(NarratedDefinition, template.definition, DEFINITION)
    if not isinstance(definition, NarratedDefinition):
        return errors
    styled = style_problems(definition)
    checked = {
        **styled,
        **placeholder_problems(definition),
        **ui_problems(definition, template.audience, engine_ui),
    }
    return checked if styled else {**checked, **settings_problems(template, definition)}
