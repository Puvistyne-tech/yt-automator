from __future__ import annotations

from pydantic import ValidationError

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.structures.length import length_problem
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.merging import deep_merged
from autotube.pipelines.narrated_video.template.settings_model import template_defaults

LENGTH_PATH = "definition.length"


def length_problems(definition: NarratedDefinition, audience: TemplateAudience) -> dict[str, str]:
    structure: JsonObject = {"story": {"structure": definition.structure.value}}
    values = deep_merged(template_defaults(definition, audience), structure)
    try:
        settings = KidsStorySettings.model_validate(values)
    except ValidationError:
        return {}
    problem = length_problem(settings)
    return {LENGTH_PATH: problem} if problem else {}
