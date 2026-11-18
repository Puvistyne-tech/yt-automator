from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from automator.domain.channels import ChannelDefaults
from automator.domain.run_enums import ReviewDecision
from automator.domain.settings import AppSettingsInput


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConnectChannelRequest(RequestModel):
    credential_id: str = Field(min_length=1, description="Credential to authorize with")


class ChannelPatchRequest(RequestModel):
    defaults: ChannelDefaults = Field(description="Upload defaults for the channel")


class EnabledRequest(RequestModel):
    enabled: bool = Field(description="Whether the automation runs on its schedule")


class RetryRequest(RequestModel):
    from_stage: str | None = Field(default=None, description="Stage to restart from")


class ReviewRequest(RequestModel):
    decision: ReviewDecision = Field(description="approved or rejected")
    notes: str = Field(default="", description="Reviewer notes")


class SecretValueRequest(RequestModel):
    value: str = Field(min_length=1, repr=False, description="Secret value, never returned")


class SettingsRequest(AppSettingsInput):
    data_dir: str | None = Field(default=None, description="Read-only, ignored when sent")

    def changes(self) -> AppSettingsInput:
        return AppSettingsInput(**self.model_dump(exclude={"data_dir"}))
