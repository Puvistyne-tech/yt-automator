from __future__ import annotations

from dataclasses import dataclass

from automator.application.publish_run import PublishRun
from automator.application.run_recorder import RunRecorder
from automator.domain.ports import RunRepository
from automator.domain.run_enums import LogLevel, RunStatus
from automator.domain.runs import Run
from automator.shared.errors import AppError

STARTING = "Publishing automatically after approval"


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
            return self.publisher.execute(run.id)
        except AppError as error:
            self.recorder.log(run.id, f"Auto-publish stopped: {error.message}", LogLevel.WARNING)
            return self.runs.get(run.id) or run
