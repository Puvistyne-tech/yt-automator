from __future__ import annotations

from pydantic import AwareDatetime, Field

from automator.domain.channels import Privacy
from automator.domain.model_base import DomainModel, JsonObject
from automator.domain.quality import ReviewPolicy
from automator.domain.retries import RetryPolicy
from automator.domain.runs import RunSummary
from automator.domain.schedules import Schedule


class TargetFields(DomainModel):
    channel_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    variants: tuple[str, ...] = Field(min_length=1)
    privacy: Privacy | None = None
    made_for_kids: bool | None = None
    playlist_id: str | None = None
    publish_delay_minutes: int = Field(
        default=0,
        ge=0,
        description="Public videos only: upload private and go public this many minutes later.",
    )
    publish_time_of_day: str | None = Field(
        default=None,
        description=(
            "Public videos only, instead of a delay: upload private and go public at the next "
            "HH:MM (24-hour) in publish_timezone after publishing starts."
        ),
    )
    publish_timezone: str = Field(
        default="UTC", description="IANA time zone for publish_time_of_day."
    )


class TargetInput(TargetFields):
    id: str | None = None


class Target(TargetFields):
    id: str


class AutomationFields(DomainModel):
    name: str = Field(min_length=1)
    description: str = ""
    pipeline_type: str = Field(min_length=1)
    settings: JsonObject = Field(default_factory=dict)
    languages: tuple[str, ...] = Field(min_length=1)
    schedule: Schedule = Field(default_factory=Schedule)
    review_policy: ReviewPolicy = Field(default_factory=ReviewPolicy)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    enabled: bool = True


class AutomationInput(AutomationFields):
    targets: tuple[TargetInput, ...] = ()


class Automation(AutomationFields):
    id: str
    targets: tuple[Target, ...] = ()
    created_at: AwareDatetime
    updated_at: AwareDatetime
    next_run_at: AwareDatetime | None = None
    last_run: RunSummary | None = None

    def as_input(self) -> AutomationInput:
        fields = self.model_dump(include=set(AutomationFields.model_fields))
        targets = tuple(TargetInput(**target.model_dump()) for target in self.targets)
        return AutomationInput(**fields, targets=targets)

    def targets_channel(self, channel_id: str) -> bool:
        return any(target.channel_id == channel_id for target in self.targets)
