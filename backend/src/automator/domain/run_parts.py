from __future__ import annotations

from pydantic import AwareDatetime, Field

from automator.domain.channels import Privacy
from automator.domain.model_base import DomainModel, JsonObject
from automator.domain.run_enums import (
    ArtifactKind,
    LogLevel,
    ReviewDecision,
    StageStatus,
    UploadStatus,
)


class StageRun(DomainModel):
    stage_id: str
    title: str
    status: StageStatus = StageStatus.PENDING
    provider: str = ""
    message: str = ""
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None


class Artifact(DomainModel):
    id: str
    kind: ArtifactKind
    stage_id: str
    language: str | None = None
    variant: str | None = None
    filename: str
    media_type: str
    size_bytes: int = Field(ge=0)
    meta: JsonObject = Field(default_factory=dict)


class Review(DomainModel):
    decision: ReviewDecision
    notes: str = ""
    decided_at: AwareDatetime


class Upload(DomainModel):
    target_id: str
    channel_id: str
    language: str
    variant: str
    status: UploadStatus = UploadStatus.PENDING
    youtube_video_id: str | None = None
    url: str | None = None
    error: str | None = None
    quota_units: int = Field(default=0, ge=0)
    privacy: Privacy | None = None
    made_for_kids: bool | None = None


class RunLog(DomainModel):
    at: AwareDatetime
    level: LogLevel = LogLevel.INFO
    stage_id: str | None = None
    message: str


DEFAULT_MAX_RUN_LOGS = 2000


class RunLogPolicy(DomainModel):
    max_entries: int = Field(default=DEFAULT_MAX_RUN_LOGS, ge=1)

    def appended(self, logs: tuple[RunLog, ...], entry: RunLog) -> tuple[RunLog, ...]:
        return (*logs, entry)[-self.max_entries :]
