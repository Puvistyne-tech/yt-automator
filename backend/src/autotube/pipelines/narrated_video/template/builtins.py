from __future__ import annotations

from functools import cache

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import (
    USER_TYPE_PREFIX,
    PipelineTemplate,
    TemplateAudience,
    builtin_template,
)
from autotube.pipelines.narrated_video.resources import resource_json, resource_names

FOLDER = "builtins"


class DuplicateBuiltinError(ValueError):
    pass


class PackagedTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    audience: TemplateAudience
    definition: JsonObject

    @field_validator("id")
    @classmethod
    def not_a_user_type_id(cls, value: str) -> str:
        if value.startswith(USER_TYPE_PREFIX):
            raise ValueError(f"ids starting with {USER_TYPE_PREFIX!r} belong to user templates")
        return value

    def template(self, engine_id: str) -> PipelineTemplate:
        return builtin_template(
            engine_id, self.id, self.name, self.description, self.audience, self.definition
        )


def unique_entries(entries: tuple[PackagedTemplate, ...]) -> tuple[PackagedTemplate, ...]:
    ids = [entry.id for entry in entries]
    repeated = sorted({found for found in ids if ids.count(found) > 1})
    if repeated:
        raise DuplicateBuiltinError(
            f"packaged built-in templates repeat the ids {', '.join(map(repr, repeated))}"
        )
    return entries


@cache
def packaged_entries() -> tuple[PackagedTemplate, ...]:
    return unique_entries(
        tuple(
            PackagedTemplate.model_validate(resource_json(FOLDER, name))
            for name in resource_names(FOLDER, ".json")
        )
    )


def packaged_templates(engine_id: str) -> list[PipelineTemplate]:
    return [entry.template(engine_id) for entry in packaged_entries()]
