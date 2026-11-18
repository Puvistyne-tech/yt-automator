from __future__ import annotations

from dataclasses import dataclass

from automator.application.publish_run import PublishRun
from automator.application.run_recorder import RunRecorder
from automator.domain.ports import RunRepository
from automator.domain.publish_outcome import NO_UPLOAD_SUCCEEDED
from automator.domain.run_enums import LogLevel, RunStatus
from automator.domain.runs import Run
from automator.shared.errors import AppError

STARTING = "Publishing automatically after approval"


def stopped_message(reason: str) -> str:
    return f"Auto-publish stopped: {reason}"


def publishes_on_approval(run: Run) -> bool:
    return run.status is RunStatus.APPROVED and run.review_policy.auto_publish


@dataclass(frozen=True)
class AutoPublish:
    runs: RunRepository
    publisher: PublishRun
    recorder: RunRecorder

    def after_approval(self, run: Run) -> Run:
        if not publishes_on_approval(run):
            return run
        self.recorder.log(run.id, STARTING)
        try:
            published = self.publisher.execute(run.id)
        except AppError as error:
            return self.stopped(run, error.message)
        if published.status is RunStatus.APPROVED:
            return self.stopped(published, published.error or NO_UPLOAD_SUCCEEDED)
        return published

    def stopped(self, run: Run, reason: str) -> Run:
        self.recorder.log(run.id, stopped_message(reason), LogLevel.WARNING)
        return self.runs.get(run.id) or run
