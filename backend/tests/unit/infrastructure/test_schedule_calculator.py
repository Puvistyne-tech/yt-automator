from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from autotube.domain.schedule_timing import next_run_at
from autotube.domain.schedules import Schedule, ScheduleKind
from autotube.infrastructure.scheduling.schedule_calculator import StandardScheduleCalculator

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


def one_start(day: date) -> int:
    return 1 if day == AFTER.date() else 0


def test_calculator_passes_the_start_counter_through() -> None:
    capped = Schedule(kind=ScheduleKind.INTERVAL, every_hours=1, max_runs_per_day=1)
    found = StandardScheduleCalculator().next_run_at(capped, AFTER, one_start)
    assert found == next_run_at(capped, AFTER, one_start) == datetime(2026, 1, 6, tzinfo=UTC)
