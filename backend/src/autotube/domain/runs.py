from __future__ import annotations

from pydantic import AwareDatetime, Field

from autotube.domain.model_base import DomainModel, JsonObject
from autotube.domain.quality import ReviewPolicy, ScoreItem
from autotube.domain.retries import RetryPolicy
from autotube.domain.run_enums import RunEventKind, RunStatus, RunTrigger
from autotube.domain.run_parts import Artifact, Review, RunLog, StageRun, Upload


class RunSummary(DomainModel):
    id: str
    status: RunStatus
    score: float | None = None
    created_at: AwareDatetime
    finished_at: AwareDatetime | None = None


class Run(DomainModel):
    id: str
    automation_id: str
    automation_name: str
    pipeline_type: str
    status: RunStatus = RunStatus.QUEUED
    trigger: RunTrigger = RunTrigger.MANUAL
    languages: tuple[str, ...]
    settings_snapshot: JsonObject
    review_policy: ReviewPolicy = Field(default_factory=ReviewPolicy)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    auto_retries: int = Field(default=0, ge=0)
    retry_at: AwareDatetime | None = None
    skipped_start_at: AwareDatetime | None = None
    stages: tuple[StageRun, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    score: float | None = None
    score_details: tuple[ScoreItem, ...] = ()
    review: Review | None = None
    uploads: tuple[Upload, ...] = ()
    logs: tuple[RunLog, ...] = ()
    error: str | None = None
    created_at: AwareDatetime
    started_at: AwareDatetime | None = None
    finished_at: AwareDatetime | None = None
    intermediate_removed_at: AwareDatetime | None = None

    def summary(self) -> RunSummary:
        return RunSummary(
            id=self.id,
            status=self.status,
            score=self.score,
            created_at=self.created_at,
            finished_at=self.finished_at,
        )

    def stage(self, stage_id: str) -> StageRun | None:
        return next((stage for stage in self.stages if stage.stage_id == stage_id), None)


class RunEvent(DomainModel):
    run_id: str
    kind: RunEventKind
    at: AwareDatetime
    payload: JsonObject = Field(default_factory=dict)


class RunQuery(DomainModel):
    automation_id: str | None = None
    status: RunStatus | None = None
    trigger: RunTrigger | None = None
    created_after: AwareDatetime | None = None
    limit: int | None = Field(default=None, ge=1)
