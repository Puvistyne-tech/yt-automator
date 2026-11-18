from __future__ import annotations

from datetime import datetime

from automator.domain.schedule_timing import StartCounter, next_run_at, no_starts
from automator.domain.schedules import Schedule


class StandardScheduleCalculator:
    def next_run_at(
        self, schedule: Schedule, after: datetime, started_on: StartCounter = no_starts
    ) -> datetime | None:
        return next_run_at(schedule, after, started_on)
