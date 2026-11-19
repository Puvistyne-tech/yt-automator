from __future__ import annotations

from datetime import datetime

from pydantic import Field

from autotube.domain.model_base import DomainModel, JsonObject
from autotube.domain.pipeline_templates import (
    PipelineTemplate,
    TemplateAudience,
    TemplateOrigin,
    TemplateStatus,
    user_type_id,
)
from autotube.domain.template_rules import name_errors, origin_errors

EDITABLE_FIELDS = frozenset({"description", "audience", "status", "definition"})


class TemplateInput(DomainModel):
    engine: str = Field(
        min_length=1, description="Engine that turns the definition into a pipeline"
    )
    name: str = Field(description="Name shown when choosing a pipeline")
    description: str = Field(default="", description="What videos this pipeline makes")
    audience: TemplateAudience = Field(description="Who the videos are for; fixed after creation")
    status: TemplateStatus = Field(
        default=TemplateStatus.DRAFT, description="Only ready templates are offered to automations"
    )
    origin: TemplateOrigin = Field(
        default=TemplateOrigin.BLANK, description="How the template was started"
    )
    definition: JsonObject = Field(
        default_factory=dict, description="Engine definition, described by its definition schema"
    )


def input_errors(data: TemplateInput) -> dict[str, str]:
    return origin_errors(data.origin) | name_errors(data.name)


def new_template(data: TemplateInput, template_id: str, now: datetime) -> PipelineTemplate:
    return PipelineTemplate(
        id=template_id,
        type_id=user_type_id(template_id),
        engine=data.engine,
        name=data.name.strip(),
        description=data.description,
        audience=data.audience,
        status=data.status,
        origin=data.origin,
        definition=data.definition,
        created_at=now,
        updated_at=now,
    )


def changed(current: PipelineTemplate, data: TemplateInput) -> PipelineTemplate:
    edits = {field: getattr(data, field) for field in EDITABLE_FIELDS}
    return current.model_copy(update=edits | {"name": data.name.strip()})


def duplicated(
    source: PipelineTemplate,
    template_id: str,
    name: str,
    audience: TemplateAudience | None,
    now: datetime,
) -> PipelineTemplate:
    copy = {
        "id": template_id,
        "type_id": user_type_id(template_id),
        "name": name.strip(),
        "audience": audience or source.audience,
        "status": TemplateStatus.DRAFT,
        "origin": TemplateOrigin.DUPLICATE,
        "revision": 1,
        "created_at": now,
        "updated_at": now,
    }
    return source.model_copy(update=copy)
