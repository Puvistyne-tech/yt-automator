from __future__ import annotations

from dataclasses import dataclass

from automator.domain.ports import Clock, RunQueue, RunRepository
from automator.domain.run_enums import RunStatus, StageStatus, UploadStatus
from automator.domain.run_parts import StageRun, Upload
from automator.domain.runs import Run, RunQuery

INTERRUPTED_STATUSES = (RunStatus.RUNNING, RunStatus.PUBLISHING)
UNFINISHED_UPLOADS = frozenset({UploadStatus.PENDING, UploadStatus.UPLOADING})
INTERRUPTED_MESSAGE = "interrupted: the app stopped while the run was {status}"


@dataclass(frozen=True)
class RecoveryReport:
    failed: tuple[str, ...]
    requeued: tuple[str, ...]


def interrupted_stage(stage: StageRun, run: Run, message: str) -> StageRun:
    if stage.status is not StageStatus.RUNNING:
        return stage
    return stage.model_copy(
        update={"status": StageStatus.FAILED, "message": message, "finished_at": run.finished_at}
    )


def interrupted_upload(upload: Upload, message: str) -> Upload:
    if upload.status not in UNFINISHED_UPLOADS:
        return upload
    return upload.model_copy(update={"status": UploadStatus.FAILED, "error": message})


def failed_after_crash(run: Run, clock: Clock) -> Run:
    message = INTERRUPTED_MESSAGE.format(status=run.status.value)
    failed = run.model_copy(
        update={"status": RunStatus.FAILED, "error": message, "finished_at": clock.now()}
    )
    return failed.model_copy(
        update={
            "stages": tuple(interrupted_stage(s, failed, message) for s in failed.stages),
            "uploads": tuple(interrupted_upload(u, message) for u in failed.uploads),
        }
    )


def recover_interrupted_runs(runs: RunRepository, queue: RunQueue, clock: Clock) -> RecoveryReport:
    failed: list[str] = []
    for status in INTERRUPTED_STATUSES:
        for run in runs.list(RunQuery(status=status)):
            runs.save(failed_after_crash(run, clock))
            failed.append(run.id)
    queued = sorted(runs.list(RunQuery(status=RunStatus.QUEUED)), key=lambda run: run.created_at)
    for run in queued:
        queue.enqueue(run.id)
    return RecoveryReport(failed=tuple(failed), requeued=tuple(run.id for run in queued))
