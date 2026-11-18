from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from automator.application.automation_presenter import AutomationPresenter
from automator.application.start_run import StartRun
from automator.domain.automations import Automation
from automator.domain.ports import AutomationRepository
from automator.domain.run_enums import RunTrigger
from automator.domain.runs import Run
from automator.shared.errors import AppError


@dataclass(frozen=True)
class RunDueAutomations:
    automations: AutomationRepository
    presenter: AutomationPresenter
    start_run: StartRun

    def is_due(self, automation: Automation, now: datetime) -> bool:
        next_run = self.presenter.next_run_at(automation)
        return next_run is not None and next_run <= now

    def execute(self, now: datetime) -> list[Run]:
        started: list[Run] = []
        for automation in self.automations.list():
            if not self.is_due(automation, now):
                continue
            try:
                started.append(self.start_run.execute(automation.id, RunTrigger.SCHEDULE))
            except AppError:
                continue
        return started
