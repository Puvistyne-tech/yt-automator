from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import AwareDatetime, Field

from autotube.domain.model_base import DomainModel, JsonObject

USER_TYPE_PREFIX = "t_"
BUILTIN_RELEASED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class TemplateAudience(StrEnum):
    KIDS = "kids"
    GENERAL = "general"


class TemplateStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class TemplateOrigin(StrEnum):
    BUILTIN = "builtin"
    BLANK = "blank"
    DUPLICATE = "duplicate"
    SUGGESTED = "suggested"


class PipelineTemplate(DomainModel):
    id: str = Field(min_length=1)
    type_id: str = Field(min_length=1)
    engine: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    audience: TemplateAudience
    status: TemplateStatus = TemplateStatus.DRAFT
    origin: TemplateOrigin
    revision: int = Field(default=1, ge=1)
    definition: JsonObject = Field(default_factory=dict)
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @property
    def is_builtin(self) -> bool:
        return self.origin is TemplateOrigin.BUILTIN

    @property
    def is_ready(self) -> bool:
        return self.status is TemplateStatus.READY


def user_type_id(template_id: str) -> str:
    return f"{USER_TYPE_PREFIX}{template_id}"


def builtin_template(
    engine: str,
    type_id: str,
    name: str,
    description: str,
    audience: TemplateAudience,
    definition: JsonObject,
) -> PipelineTemplate:
    return PipelineTemplate(
        id=type_id,
        type_id=type_id,
        engine=engine,
        name=name,
        description=description,
        audience=audience,
        status=TemplateStatus.READY,
        origin=TemplateOrigin.BUILTIN,
        definition=definition,
        created_at=BUILTIN_RELEASED_AT,
        updated_at=BUILTIN_RELEASED_AT,
    )
