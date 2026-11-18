from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import Field

from automator.domain.cron import cron_error, next_cron_time, parse_cron
from automator.domain.model_base import DomainModel
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


MIN_INTERVAL_HOURS = 1


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


def schedule_errors(schedule: Schedule) -> dict[str, str]:
    errors: dict[str, str] = {}
    if find_zone(schedule.timezone) is None:
        errors["timezone"] = f"unknown timezone {schedule.timezone!r}"
    if schedule.kind is ScheduleKind.INTERVAL:
        errors |= interval_errors(schedule)
    if schedule.kind is ScheduleKind.CRON:
        errors |= cron_errors(schedule)
    return errors


def _epoch() -> datetime:
    return datetime.fromisoformat("2000-01-01T00:00:00+00:00")


def next_run_at(schedule: Schedule, after: datetime) -> datetime | None:
    require_aware(after)
    if schedule_errors(schedule):
        return None
    if schedule.kind is ScheduleKind.INTERVAL and schedule.every_hours is not None:
        return to_utc(after) + timedelta(hours=schedule.every_hours)
    zone = find_zone(schedule.timezone)
    if schedule.kind is ScheduleKind.CRON and schedule.cron and zone is not None:
        return next_cron_time(parse_cron(schedule.cron), after, zone)
    return None


class StandardScheduleCalculator:
    def next_run_at(self, schedule: Schedule, after: datetime) -> datetime | None:
        return next_run_at(schedule, after)
