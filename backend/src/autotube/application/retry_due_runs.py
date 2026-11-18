from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import partial

from autotube.application.retry_run import RetryRun, retry_reset, retry_start
from autotube.application.run_recorder import RunRecorder
from autotube.domain.ports import RunRepository
from autotube.domain.run_enums import RunStatus
from autotube.domain.run_state import retry_due
from autotube.domain.runs import Run, RunQuery
from autotube.shared.errors import AppError, RuleConflict


def automatic_retry_reset(now: datetime, stored: Run) -> Run:
    if not retry_due(stored, now):
        raise RuleConflict("retry_not_due", f"run {stored.id} has no automatic retry due")
    return retry_reset(None, stored).model_copy(update={"auto_retries": stored.auto_retries + 1})


def retry_message(queued: Run, failure: str | None) -> str:
    stage = queued.stages[retry_start(queued, None)].stage_id if queued.stages else "start"
    attempt = f"{queued.auto_retries} of {queued.retry_policy.auto_retry_count}"
    return f"Automatic retry {attempt} from stage {stage} after: {failure or 'failure'}"


@dataclass(frozen=True)
class RetryDueRuns:
    runs: RunRepository
    retry: RetryRun
    recorder: RunRecorder

    def due(self, now: datetime) -> list[Run]:
        failed = self.runs.list(RunQuery(status=RunStatus.FAILED))
        return sorted(
            (run for run in failed if retry_due(run, now)), key=lambda run: run.created_at
        )

    def retried(self, run: Run, now: datetime) -> Run | None:
        try:
            queued = self.retry.requeue(run.id, partial(automatic_retry_reset, now))
        except AppError:
            return None
        self.recorder.log(queued.id, retry_message(queued, run.error))
        return self.runs.get(queued.id) or queued

    def execute(self, now: datetime) -> list[Run]:
        retried = (self.retried(run, now) for run in self.due(now))
        return [run for run in retried if run is not None]
