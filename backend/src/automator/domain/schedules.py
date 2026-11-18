from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import Field

from automator.domain.cron import cron_error, next_cron_time, parse_cron
from automator.domain.local_times import time_of_day_errors
from automator.domain.model_base import DomainModel
from automator.domain.validation import timezone_errors
from automator.shared.clock import find_zone, require_aware, to_utc


class ScheduleKind(StrEnum):
    MANUAL = "manual"
    INTERVAL = "interval"
    CRON = "cron"


class Schedule(DomainModel):
    kind: ScheduleKind = ScheduleKind.MANUAL
    every_hours: int | None = None
    cron: str | None = None
    timezone: str = Field(default="UTC")
    skip_if_unfinished: bool = Field(
        default=True,
        description="Skip a scheduled start while a run of this automation is still unfinished.",
    )
    max_runs_per_day: int | None = Field(
        default=None,
        ge=1,
        description="Start no scheduled run once this many runs started that day. Empty: no cap.",
    )
    active_from: str | None = Field(
        default=None, description="Start scheduled runs only from this HH:MM (24-hour)."
    )
    active_until: str | None = Field(
        default=None, description="Start scheduled runs only before this HH:MM (24-hour)."
    )


MIN_INTERVAL_HOURS = 1
BOTH_ACTIVE_HOURS = "set both the start and the end of the active hours, or neither"


def interval_errors(schedule: Schedule) -> dict[str, str]:
    if schedule.every_hours is None or schedule.every_hours < MIN_INTERVAL_HOURS:
        return {"every_hours": f"must be at least {MIN_INTERVAL_HOURS}"}
    return {}


def cron_errors(schedule: Schedule) -> dict[str, str]:
    if not schedule.cron:
        return {"cron": "a 5-field cron expression is required"}
    problem = cron_error(schedule.cron)
    if problem is not None:
        return {"cron": problem}
    zone = find_zone(schedule.timezone)
    if zone is not None and next_cron_time(parse_cron(schedule.cron), _epoch(), zone) is None:
        return {"cron": "expression never matches a date"}
    return {}


def active_hours_errors(schedule: Schedule) -> dict[str, str]:
    start, end = schedule.active_from, schedule.active_until
    errors = time_of_day_errors(start, "active_from") | time_of_day_errors(end, "active_until")
    if start is None and end is not None:
        errors.setdefault("active_from", BOTH_ACTIVE_HOURS)
    if end is None and start is not None:
        errors.setdefault("active_until", BOTH_ACTIVE_HOURS)
    if start is not None and start == end:
        errors.setdefault("active_until", "must differ from the start of the active hours")
    return errors


def schedule_errors(schedule: Schedule) -> dict[str, str]:
    errors = timezone_errors(schedule.timezone) | active_hours_errors(schedule)
    if schedule.kind is ScheduleKind.INTERVAL:
        errors |= interval_errors(schedule)
    if schedule.kind is ScheduleKind.CRON:
        errors |= cron_errors(schedule)
    return errors


def _epoch() -> datetime:
    return datetime.fromisoformat("2000-01-01T00:00:00+00:00")


def next_slot(schedule: Schedule, after: datetime) -> datetime | None:
    require_aware(after)
    if schedule_errors(schedule):
        return None
    if schedule.kind is ScheduleKind.INTERVAL and schedule.every_hours is not None:
        return to_utc(after) + timedelta(hours=schedule.every_hours)
    return cron_slot(schedule, after)


def cron_slot(schedule: Schedule, after: datetime) -> datetime | None:
    zone = find_zone(schedule.timezone)
    if schedule.kind is ScheduleKind.CRON and schedule.cron and zone is not None:
        return next_cron_time(parse_cron(schedule.cron), after, zone)
    return None


def first_slot_from(schedule: Schedule, moment: datetime) -> datetime | None:
    if schedule.kind is ScheduleKind.INTERVAL:
        return to_utc(moment)
    return cron_slot(schedule, moment - timedelta(seconds=1))
