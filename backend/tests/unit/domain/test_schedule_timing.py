from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from automator.domain.schedule_timing import NEVER_STARTS, next_run_at, schedule_start_errors
from automator.domain.schedules import BOTH_ACTIVE_HOURS, Schedule, ScheduleKind, schedule_errors

AFTER = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


def every(hours: int, **fields: Any) -> Schedule:
    return Schedule(kind=ScheduleKind.INTERVAL, every_hours=hours, **fields)


def cron(expression: str, **fields: Any) -> Schedule:
    return Schedule(kind=ScheduleKind.CRON, cron=expression, **fields)


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 1, day, hour, minute, tzinfo=UTC)


def counter(starts: dict[date, int]) -> Any:
    return lambda day: starts.get(day, 0)


DAYTIME: dict[str, Any] = {"active_from": "08:00", "active_until": "20:00"}


@pytest.mark.parametrize(
    ("anchor", "expected"),
    [
        (at(5, 8), at(5, 14)),
        (at(5, 14), at(6, 8)),
        (at(5, 21), at(6, 8)),
        (at(5, 1), at(5, 8)),
    ],
)
def test_interval_waits_for_the_active_hours(anchor: datetime, expected: datetime) -> None:
    assert next_run_at(every(6, **DAYTIME), anchor) == expected


def test_active_hours_can_cross_midnight() -> None:
    night = every(2, active_from="22:00", active_until="02:00")
    assert next_run_at(night, at(5, 22)) == at(6, 0)
    assert next_run_at(night, at(6, 0)) == at(6, 22)


def test_cron_skips_matches_outside_the_active_hours() -> None:
    hourly = cron("30 * * * *", active_from="09:00", active_until="11:00")
    assert next_run_at(hourly, at(5, 10, 30)) == at(6, 9, 30)


def test_active_hours_follow_the_schedule_zone() -> None:
    kolkata = every(1, timezone="Asia/Kolkata", active_from="09:00", active_until="17:00")
    assert next_run_at(kolkata, at(5, 11, 30)) == at(6, 3, 30)


def test_the_daily_cap_moves_the_start_to_the_next_day() -> None:
    capped = every(6, max_runs_per_day=2)
    full = counter({date(2026, 1, 5): 2})
    assert next_run_at(capped, at(5, 12), full) == at(6, 0)
    assert next_run_at(capped, at(5, 12), counter({date(2026, 1, 5): 1})) == at(5, 18)


def test_the_cap_and_active_hours_combine() -> None:
    both = every(6, max_runs_per_day=1, **DAYTIME)
    assert next_run_at(both, at(5, 8), counter({date(2026, 1, 5): 1})) == at(6, 8)


def test_the_cap_counts_days_in_the_schedule_zone() -> None:
    seen: list[date] = []

    def record(day: date) -> int:
        seen.append(day)
        return 0

    next_run_at(every(1, timezone="Asia/Kolkata", max_runs_per_day=3), at(5, 20), record)
    assert seen == [date(2026, 1, 6)]


def test_a_cron_that_never_matches_inside_active_hours_never_starts() -> None:
    early = cron("0 3 * * *", **DAYTIME)
    assert next_run_at(early, AFTER) is None
    assert schedule_start_errors(early) == {"active_from": NEVER_STARTS}


def test_spring_forward_opening_inside_the_gap_moves_forward() -> None:
    gap = every(1, timezone="America/New_York", active_from="02:30", active_until="05:00")
    found = next_run_at(gap, datetime(2026, 3, 8, 5, 0, tzinfo=UTC))
    assert found == datetime(2026, 3, 8, 7, 30, tzinfo=UTC)


def test_autumn_overlap_keeps_starting_inside_the_window() -> None:
    zone = {"timezone": "America/New_York"}
    overlap = every(1, active_from="01:00", active_until="02:00", **zone)
    first = next_run_at(overlap, datetime(2026, 11, 1, 4, 30, tzinfo=UTC))
    assert first == datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
    second = next_run_at(overlap, first or AFTER)
    assert second == datetime(2026, 11, 1, 6, 30, tzinfo=UTC)


def test_an_unknown_zone_never_runs() -> None:
    assert next_run_at(every(1, timezone="Nowhere/City"), AFTER) is None


def test_a_manual_schedule_has_no_start_errors() -> None:
    assert schedule_start_errors(Schedule(**DAYTIME)) == {}
    assert schedule_start_errors(every(6, **DAYTIME)) == {}
    assert schedule_start_errors(every(0)) == {"every_hours": "must be at least 1"}


@pytest.mark.parametrize(
    ("fields", "errors"),
    [
        ({"active_from": "08:00"}, {"active_until": BOTH_ACTIVE_HOURS}),
        ({"active_until": "08:00"}, {"active_from": BOTH_ACTIVE_HOURS}),
        (
            {"active_from": "08:00", "active_until": "08:00"},
            {"active_until": "must differ from the start of the active hours"},
        ),
        (
            {"active_from": "8", "active_until": "20:00"},
            {"active_from": "'8' is not a time of day: use a 24-hour time such as 08:00"},
        ),
        ({"active_from": "20:00", "active_until": "08:00"}, {}),
    ],
)
def test_active_hours_errors(fields: dict[str, str], errors: dict[str, str]) -> None:
    assert schedule_errors(Schedule.model_validate(fields)) == errors


def test_schedules_stored_before_the_new_options_load_with_defaults() -> None:
    stored = Schedule.model_validate({"kind": "interval", "every_hours": 6, "timezone": "UTC"})
    assert stored.skip_if_unfinished is True
    assert (stored.max_runs_per_day, stored.active_from, stored.active_until) == (None, None, None)
