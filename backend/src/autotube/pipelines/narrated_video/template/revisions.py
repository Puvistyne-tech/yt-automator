from __future__ import annotations

from pydantic import JsonValue

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.pipelines.narrated_video.settings.story_choices import Structure

STRUCTURE_FIELD = "structure"
FIXED_STRUCTURE = "structure cannot change after creation; duplicate the template instead"


def structure_value(definition: JsonObject) -> JsonValue:
    return definition.get(STRUCTURE_FIELD, Structure.STORY.value)


def structure_change_problems(
    current: PipelineTemplate, proposed: PipelineTemplate
) -> dict[str, str]:
    if structure_value(current.definition) == structure_value(proposed.definition):
        return {}
    return {f"definition.{STRUCTURE_FIELD}": FIXED_STRUCTURE}
