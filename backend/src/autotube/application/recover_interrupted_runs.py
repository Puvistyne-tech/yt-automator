from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from autotube.application.run_progress import RunProgress
from autotube.application.run_recorder import RunRecorder
from autotube.domain.ports import Clock, RunQueue, RunRepository
from autotube.domain.publish_outcome import is_unfinished, publish_outcome
from autotube.domain.run_enums import RunStatus, StageStatus, UploadStatus
from autotube.domain.run_parts import StageRun, Upload
from autotube.domain.runs import Run, RunQuery

INTERRUPTED_RUN_ERROR = "interrupted: the app stopped while the run was running"
INTERRUPTED_UPLOAD_ERROR = "interrupted, check YouTube before publishing again"


@dataclass(frozen=True)
class RecoveryReport:
    failed: tuple[str, ...]
    settled: tuple[str, ...]
    requeued: tuple[str, ...]

    def total(self) -> int:
        return len(self.failed) + len(self.settled) + len(self.requeued)


def interrupted_stage(stage: StageRun, at: datetime) -> StageRun:
    return stage.model_copy(
        update={"status": StageStatus.FAILED, "message": INTERRUPTED_RUN_ERROR, "finished_at": at}
    )


def interrupted_upload(upload: Upload) -> Upload:
    return upload.model_copy(
        update={"status": UploadStatus.FAILED, "error": INTERRUPTED_UPLOAD_ERROR}
    )


def is_running(run: Run) -> bool:
    return run.status is RunStatus.RUNNING


@dataclass(frozen=True)
class RecoverInterruptedRuns:
    runs: RunRepository
    recorder: RunRecorder
    progress: RunProgress
    queue: RunQueue
    clock: Clock

    def execute(self) -> RecoveryReport:
        failed = tuple(self.fail_running(run) for run in self.with_status(RunStatus.RUNNING))
        settled = tuple(self.settle(run) for run in self.with_status(RunStatus.PUBLISHING))
        queued = sorted(self.with_status(RunStatus.QUEUED), key=lambda run: run.created_at)
        for run in queued:
            self.queue.enqueue(run.id)
        return RecoveryReport(failed, settled, tuple(run.id for run in queued))

    def with_status(self, status: RunStatus) -> list[Run]:
        return self.runs.list(RunQuery(status=status))

    def fail_running(self, run: Run) -> str:
        for stage in run.stages:
            if stage.status is StageStatus.RUNNING:
                stopped = interrupted_stage(stage, self.clock.now())
                run = self.recorder.stage(run.id, stopped, is_running) or run
        self.progress.fail(run, INTERRUPTED_RUN_ERROR)
        return run.id

    def settle(self, run: Run) -> str:
        for index, upload in enumerate(run.uploads):
            if is_unfinished(upload):
                run = self.recorder.upload(run.id, index, interrupted_upload(upload))
        status, error = publish_outcome(run.uploads)
        return self.progress.move(run.id, status, error).id
