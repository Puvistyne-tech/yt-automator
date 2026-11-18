from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import partial

from autotube.domain.automations import Automation
from autotube.domain.local_times import local_instant
from autotube.domain.ports import RunRepository, ScheduleCalculator
from autotube.domain.run_enums import RunTrigger
from autotube.domain.runs import Run, RunQuery
from autotube.domain.schedules import ScheduleKind
from autotube.shared.clock import find_zone


def schedule_moments(runs: list[Run]) -> list[datetime]:
    created = [run.created_at for run in runs if run.trigger is RunTrigger.SCHEDULE]
    skipped = [run.skipped_start_at for run in runs if run.skipped_start_at is not None]
    return created + skipped


@dataclass(frozen=True)
class AutomationPresenter:
    runs: RunRepository
    schedules: ScheduleCalculator

    def latest_run(self, automation_id: str, trigger: RunTrigger | None = None) -> Run | None:
        found = self.runs.list(RunQuery(automation_id=automation_id, trigger=trigger, limit=1))
        return found[0] if found else None

    def schedule_anchor(self, automation: Automation) -> datetime:
        last = self.latest_run(automation.id, RunTrigger.SCHEDULE)
        since = last.created_at if last is not None else None
        recent = self.runs.list(RunQuery(automation_id=automation.id, created_after=since))
        return max([automation.updated_at, *schedule_moments(recent)])

    def started_on(self, automation: Automation, day: date) -> int:
        zone = find_zone(automation.schedule.timezone)
        if zone is None:
            return 0
        start = local_instant(day, time.min, zone)
        end = local_instant(day + timedelta(days=1), time.min, zone)
        found = self.runs.list(RunQuery(automation_id=automation.id, created_after=start))
        return sum(1 for run in found if run.created_at < end)

    def next_run_at(self, automation: Automation) -> datetime | None:
        if not automation.enabled or automation.schedule.kind is ScheduleKind.MANUAL:
            return None
        return self.schedules.next_run_at(
            automation.schedule,
            self.schedule_anchor(automation),
            partial(self.started_on, automation),
        )

    def present(self, automation: Automation) -> Automation:
        last = self.latest_run(automation.id)
        return automation.model_copy(
            update={
                "next_run_at": self.next_run_at(automation),
                "last_run": last.summary() if last is not None else None,
            }
        )
