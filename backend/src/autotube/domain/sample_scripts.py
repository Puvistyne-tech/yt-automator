from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import Field

from autotube.domain.model_base import DomainModel
from autotube.domain.pipeline_descriptors import LanguageOption
from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.domain.template_inputs import TemplateInput, new_template

PREVIEW_TEMPLATE_ID = "preview"
TOPIC_MAX_LENGTH = 300


class SampleUnavailableError(RuntimeError):
    pass


class TemplatePreviewInput(TemplateInput):
    language: str | None = Field(
        default=None, description="Language of the sample; the template's first language if empty"
    )
    topic: str = Field(
        default="",
        max_length=TOPIC_MAX_LENGTH,
        description="What this sample is about; empty lets the template choose",
    )


class SampleScene(DomainModel):
    narration: str = Field(description="What the narrator says")
    heading: str = Field(default="", description="The scene's heading, when the format has one")
    action: str = Field(default="", description="The movement shown in the scene, when written")


class SampleScript(DomainModel):
    language: str
    title: str
    scenes: tuple[SampleScene, ...]
    takeaway: str = Field(default="", description="The one thing the viewer should remember")
    upload_title: str = Field(description="The video title the upload would get")
    upload_description: str = Field(description="The video description the upload would get")
    provider: str = Field(description="Which script writer produced the sample")


def preview_template(data: TemplatePreviewInput, now: datetime) -> PipelineTemplate:
    return new_template(data, PREVIEW_TEMPLATE_ID, now)


def sample_language(requested: str | None, offered: Sequence[LanguageOption]) -> str:
    return requested or (offered[0].code if offered else "")


def sample_language_errors(language: str, offered: Sequence[LanguageOption]) -> dict[str, str]:
    codes = [option.code for option in offered]
    if language in codes:
        return {}
    return {"language": f"language must be one of: {', '.join(codes)}"}
