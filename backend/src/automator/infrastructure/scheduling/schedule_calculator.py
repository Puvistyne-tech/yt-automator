from __future__ import annotations

from datetime import datetime

from automator.domain.schedules import Schedule, next_run_at


class StandardScheduleCalculator:
    def next_run_at(self, schedule: Schedule, after: datetime) -> datetime | None:
        return next_run_at(schedule, after)
