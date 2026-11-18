from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from autotube.application.retry_due_runs import RetryDueRuns
from autotube.application.run_due_automations import RunDueAutomations
from autotube.domain.runs import Run


@dataclass(frozen=True)
class TickReport:
    retried: tuple[Run, ...]
    started: tuple[Run, ...]


@dataclass(frozen=True)
class SchedulerTick:
    retry_due: RetryDueRuns
    run_due: RunDueAutomations

    def execute(self, now: datetime) -> TickReport:
        retried = tuple(self.retry_due.execute(now))
        return TickReport(retried=retried, started=tuple(self.run_due.execute(now)))
