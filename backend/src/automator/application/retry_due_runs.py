from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import partial

from automator.application.retry_run import RetryRun, retry_reset, retry_start
from automator.application.run_recorder import RunRecorder
from automator.domain.ports import RunRepository
from automator.domain.run_enums import RunStatus
from automator.domain.run_state import retry_due
from automator.domain.runs import Run, RunQuery
from automator.shared.errors import AppError, RuleConflict


def automatic_retry_reset(now: datetime, stored: Run) -> Run:
    if not retry_due(stored, now):
        raise RuleConflict("retry_not_due", f"run {stored.id} has no automatic retry due")
    return retry_reset(None, stored).model_copy(update={"auto_retries": stored.auto_retries + 1})


def retry_message(run: Run) -> str:
    stage = run.stages[retry_start(run, None)].stage_id if run.stages else "start"
    attempt = f"{run.auto_retries + 1} of {run.retry_policy.auto_retry_count}"
    return f"Automatic retry {attempt} from stage {stage} after: {run.error or 'failure'}"


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

    def execute(self, now: datetime) -> list[Run]:
        retried: list[Run] = []
        for run in self.due(now):
            self.recorder.log(run.id, retry_message(run))
            try:
                retried.append(self.retry.requeue(run.id, partial(automatic_retry_reset, now)))
            except AppError:
                continue
        return retried
