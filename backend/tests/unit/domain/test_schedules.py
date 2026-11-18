from __future__ import annotations

from datetime import UTC, datetime

import pytest

from automator.domain.schedules import (
    Schedule,
    ScheduleKind,
    StandardScheduleCalculator,
    next_run_at,
    schedule_errors,
)

AFTER = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("schedule", "errors"),
    [
        (Schedule(), {}),
        (Schedule(kind=ScheduleKind.INTERVAL, every_hours=1), {}),
        (Schedule(kind=ScheduleKind.INTERVAL), {"every_hours": "must be at least 1"}),
        (
            Schedule(kind=ScheduleKind.INTERVAL, every_hours=0),
            {"every_hours": "must be at least 1"},
        ),
        (Schedule(kind=ScheduleKind.CRON, cron="0 9 * * *"), {}),
        (Schedule(kind=ScheduleKind.CRON), {"cron": "a 5-field cron expression is required"}),
        (
            Schedule(kind=ScheduleKind.CRON, cron="0 0 30 2 *"),
            {"cron": "expression never matches a date"},
        ),
        (Schedule(timezone="Nowhere/City"), {"timezone": "unknown timezone 'Nowhere/City'"}),
    ],
)
def test_schedule_errors(schedule: Schedule, errors: dict[str, str]) -> None:
    assert schedule_errors(schedule) == errors


def test_cron_syntax_error_is_reported_on_cron_field() -> None:
    errors = schedule_errors(Schedule(kind=ScheduleKind.CRON, cron="61 * * * *"))
    assert set(errors) == {"cron"} and "outside 0-59" in errors["cron"]


@pytest.mark.parametrize(
    ("schedule", "expected"),
    [
        (Schedule(), None),
        (Schedule(kind=ScheduleKind.INTERVAL, every_hours=6), datetime(2026, 1, 5, 16, tzinfo=UTC)),
        (Schedule(kind=ScheduleKind.INTERVAL, every_hours=0), None),
        (Schedule(kind=ScheduleKind.CRON, cron="0 9 * * *"), datetime(2026, 1, 6, 9, tzinfo=UTC)),
        (
            Schedule(kind=ScheduleKind.CRON, cron="0 9 * * *", timezone="Asia/Kolkata"),
            datetime(2026, 1, 6, 3, 30, tzinfo=UTC),
        ),
        (Schedule(kind=ScheduleKind.CRON, cron="bad"), None),
    ],
)
def test_next_run_at(schedule: Schedule, expected: datetime | None) -> None:
    assert next_run_at(schedule, AFTER) == expected
    assert StandardScheduleCalculator().next_run_at(schedule, AFTER) == expected


def test_next_run_at_requires_aware_reference() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        next_run_at(Schedule(), datetime(2026, 1, 1))
