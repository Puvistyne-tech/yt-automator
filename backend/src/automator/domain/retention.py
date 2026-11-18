from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import AwareDatetime, Field

from automator.domain.model_base import DomainModel
from automator.domain.run_enums import ArtifactKind, RunStatus
from automator.domain.run_parts import Artifact
from automator.domain.runs import Run
from automator.domain.settings import AppSettingsInput
from automator.domain.upload_hold import holds_run

S = RunStatus
FINAL_OUTPUT_KINDS = frozenset(
    {ArtifactKind.VIDEO, ArtifactKind.THUMBNAIL, ArtifactKind.SUBTITLE, ArtifactKind.METADATA}
)
PROTECTED_STATUSES = frozenset({S.QUEUED, S.RUNNING, S.AWAITING_REVIEW, S.APPROVED, S.PUBLISHING})
MEGABYTE = 1_000_000


class CleanupAction(StrEnum):
    DELETE_RUN = "delete_run"
    REMOVE_INTERMEDIATE = "remove_intermediate"
    REMOVE_ORPHAN = "remove_orphan"


class RetentionPolicy(DomainModel):
    keep_runs_days: int = Field(default=0, ge=0)
    keep_intermediate_days: int = Field(default=0, ge=0)
    publish_delays: dict[str, int] = Field(default_factory=dict)


class CleanupItem(DomainModel):
    run_id: str
    action: CleanupAction
    automation_id: str | None = None
    automation_name: str = ""
    status: RunStatus | None = None
    finished_at: AwareDatetime | None = None
    bytes: int = Field(default=0, ge=0)


class CleanupReport(DomainModel):
    dry_run: bool
    keep_runs_days: int
    keep_intermediate_days: int
    items: tuple[CleanupItem, ...] = ()
    total_bytes: int = 0


def retention_policy(settings: AppSettingsInput, delays: Mapping[str, int]) -> RetentionPolicy:
    return RetentionPolicy(
        keep_runs_days=settings.keep_runs_days,
        keep_intermediate_days=settings.keep_intermediate_days,
        publish_delays=dict(delays),
    )


def is_final_output(artifact: Artifact) -> bool:
    return artifact.kind in FINAL_OUTPUT_KINDS and artifact.language is not None


def final_artifact_ids(run: Run) -> frozenset[str]:
    return frozenset(artifact.id for artifact in run.artifacts if is_final_output(artifact))


def finished_time(run: Run) -> datetime:
    return run.finished_at or run.created_at


def has_unpublished_upload(run: Run, now: datetime, policy: RetentionPolicy) -> bool:
    finished, delays = finished_time(run), policy.publish_delays
    return any(holds_run(upload, finished, now, delays) for upload in run.uploads)


def is_protected(run: Run, now: datetime, policy: RetentionPolicy) -> bool:
    return run.status in PROTECTED_STATUSES or has_unpublished_upload(run, now, policy)


def is_older_than(run: Run, now: datetime, days: int) -> bool:
    return days > 0 and now - finished_time(run) >= timedelta(days=days)


def cleanup_action(run: Run, now: datetime, policy: RetentionPolicy) -> CleanupAction | None:
    if is_protected(run, now, policy):
        return None
    if is_older_than(run, now, policy.keep_runs_days):
        return CleanupAction.DELETE_RUN
    if is_older_than(run, now, policy.keep_intermediate_days):
        return CleanupAction.REMOVE_INTERMEDIATE
    return None


def has_intermediate_work(run: Run, intermediate_bytes: int) -> bool:
    listed = any(not is_final_output(artifact) for artifact in run.artifacts)
    return listed or intermediate_bytes > 0


def without_intermediate(run: Run, now: datetime) -> Run:
    finals = tuple(artifact for artifact in run.artifacts if is_final_output(artifact))
    removed_at = run.intermediate_removed_at or now
    return run.model_copy(update={"artifacts": finals, "intermediate_removed_at": removed_at})


def run_item(run: Run, action: CleanupAction, size: int) -> CleanupItem:
    return CleanupItem(
        run_id=run.id,
        action=action,
        automation_id=run.automation_id,
        automation_name=run.automation_name,
        status=run.status,
        finished_at=run.finished_at,
        bytes=size,
    )


def cleanup_report(
    items: Sequence[CleanupItem], policy: RetentionPolicy, dry_run: bool
) -> CleanupReport:
    return CleanupReport(
        dry_run=dry_run,
        keep_runs_days=policy.keep_runs_days,
        keep_intermediate_days=policy.keep_intermediate_days,
        items=tuple(items),
        total_bytes=sum(item.bytes for item in items),
    )


def cleanup_due(last_ran: datetime | None, now: datetime, settings: AppSettingsInput) -> bool:
    interval = settings.cleanup_interval_hours
    if not settings.auto_cleanup_enabled or interval <= 0:
        return False
    return last_ran is None or now - last_ran >= timedelta(hours=interval)


def megabytes(size: int) -> str:
    return f"{size / MEGABYTE:.1f} MB"


def working_files_removed_message(freed: int) -> str:
    return f"Cleanup removed working files ({megabytes(freed)})"
