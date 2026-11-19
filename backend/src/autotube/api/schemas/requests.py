from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotube.domain.channels import ChannelDefaults
from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.run_enums import ReviewDecision
from autotube.domain.settings import AppSettingsInput

READ_ONLY_SETTINGS = frozenset({"data_dir", "locked", "restart_required"})


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConnectChannelRequest(RequestModel):
    credential_id: str = Field(min_length=1, description="Credential to authorize with")


class ChannelPatchRequest(RequestModel):
    defaults: ChannelDefaults = Field(description="Upload defaults for the channel")


class EnabledRequest(RequestModel):
    enabled: bool = Field(description="Whether the automation runs on its schedule")


class ImportRequest(RequestModel):
    document: JsonObject = Field(description="An automation export file, as written by Export")
    channel_map: dict[str, str | None] = Field(
        default_factory=dict,
        description="Exported channel id to a connected channel id, or null to leave it out",
    )


class DuplicateTemplateRequest(RequestModel):
    name: str | None = Field(default=None, description="Name of the copy; default adds (copy)")
    audience: TemplateAudience | None = Field(
        default=None, description="Audience of the copy; default keeps the source's"
    )


class RetryRequest(RequestModel):
    from_stage: str | None = Field(default=None, description="Stage to restart from")


class ReviewRequest(RequestModel):
    decision: ReviewDecision = Field(description="approved or rejected")
    notes: str = Field(default="", description="Reviewer notes")


class SecretValueRequest(RequestModel):
    value: str = Field(min_length=1, repr=False, description="Secret value, never returned")


class SettingsRequest(AppSettingsInput):
    data_dir: str | None = Field(default=None, description="Read-only, ignored when sent")
    locked: dict[str, str] | None = Field(default=None, description="Read-only, ignored when sent")
    restart_required: list[str] | None = Field(
        default=None, description="Read-only, ignored when sent"
    )

    def sent_fields(self) -> dict[str, object]:
        return self.model_dump(exclude_unset=True, exclude=set(READ_ONLY_SETTINGS))
