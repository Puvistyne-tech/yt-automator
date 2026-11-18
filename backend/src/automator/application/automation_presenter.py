from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from automator.domain.automations import Automation
from automator.domain.ports import RunRepository, ScheduleCalculator
from automator.domain.run_enums import RunTrigger
from automator.domain.runs import Run, RunQuery
from automator.domain.schedules import ScheduleKind


@dataclass(frozen=True)
class AutomationPresenter:
    runs: RunRepository
    schedules: ScheduleCalculator

    def latest_run(self, automation_id: str, trigger: RunTrigger | None = None) -> Run | None:
        found = self.runs.list(RunQuery(automation_id=automation_id, trigger=trigger, limit=1))
        return found[0] if found else None

    def schedule_anchor(self, automation: Automation) -> datetime:
        last = self.latest_run(automation.id, RunTrigger.SCHEDULE)
        if last is None:
            return automation.updated_at
        return max(last.created_at, automation.updated_at)

    def next_run_at(self, automation: Automation) -> datetime | None:
        if not automation.enabled or automation.schedule.kind is ScheduleKind.MANUAL:
            return None
        return self.schedules.next_run_at(automation.schedule, self.schedule_anchor(automation))

    def present(self, automation: Automation) -> Automation:
        last = self.latest_run(automation.id)
        return automation.model_copy(
            update={
                "next_run_at": self.next_run_at(automation),
                "last_run": last.summary() if last is not None else None,
            }
        )
