from __future__ import annotations

from datetime import UTC, datetime

import pytest

from automator.domain.schedules import Schedule, ScheduleKind, next_run_at
from automator.infrastructure.scheduling.schedule_calculator import StandardScheduleCalculator

AFTER = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    "schedule",
    [
        Schedule(),
        Schedule(kind=ScheduleKind.INTERVAL, every_hours=6),
        Schedule(kind=ScheduleKind.CRON, cron="0 9 * * *", timezone="Asia/Kolkata"),
    ],
)
def test_calculator_delegates_to_domain_rule(schedule: Schedule) -> None:
    assert StandardScheduleCalculator().next_run_at(schedule, AFTER) == next_run_at(schedule, AFTER)
