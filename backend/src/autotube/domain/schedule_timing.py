from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from autotube.domain.local_times import (
    next_local_midnight,
    next_local_time,
    parse_time_of_day,
    within_hours,
)
from autotube.domain.schedules import (
    Schedule,
    ScheduleKind,
    first_slot_from,
    next_slot,
    schedule_errors,
)
from autotube.shared.clock import find_zone, to_utc

StartCounter = Callable[[date], int]
MAX_SHIFTS = 64
NEVER_STARTS = "the schedule never starts inside the active hours"
REFERENCE_TIME = datetime(2000, 1, 1, tzinfo=UTC)


def no_starts(_: date) -> int:
    return 0


def outside_active_hours(schedule: Schedule, moment: datetime, zone: ZoneInfo) -> datetime | None:
    start = parse_time_of_day(schedule.active_from or "")
    end = parse_time_of_day(schedule.active_until or "")
    if start is None or end is None or within_hours(moment, start, end, zone):
        return None
    return next_local_time(moment, start, zone)


def day_is_full(
    schedule: Schedule, moment: datetime, zone: ZoneInfo, started_on: StartCounter
) -> bool:
    cap = schedule.max_runs_per_day
    return cap is not None and started_on(to_utc(moment).astimezone(zone).date()) >= cap


def later_start(
    schedule: Schedule, candidate: datetime, zone: ZoneInfo, started_on: StartCounter
) -> datetime | None:
    opening = outside_active_hours(schedule, candidate, zone)
    if opening is not None:
        return opening
    if day_is_full(schedule, candidate, zone, started_on):
        return next_local_midnight(candidate, zone)
    return None


def next_run_at(
    schedule: Schedule, after: datetime, started_on: StartCounter = no_starts
) -> datetime | None:
    zone = find_zone(schedule.timezone)
    if zone is None:
        return None
    candidate = next_slot(schedule, after)
    for _ in range(MAX_SHIFTS):
        if candidate is None:
            return None
        shifted = later_start(schedule, candidate, zone, started_on)
        if shifted is None:
            return candidate
        candidate = first_slot_from(schedule, shifted)
    return None


def schedule_start_errors(schedule: Schedule) -> dict[str, str]:
    errors = schedule_errors(schedule)
    if errors or schedule.kind is ScheduleKind.MANUAL or schedule.active_from is None:
        return errors
    if next_run_at(schedule, REFERENCE_TIME) is None:
        return {"active_from": NEVER_STARTS}
    return {}
