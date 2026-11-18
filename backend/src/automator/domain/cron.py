from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from automator.domain.cron_fields import (
    DAY_OF_MONTH,
    DAY_OF_WEEK,
    HOUR,
    MINUTE,
    MONTH,
    CronSyntaxError,
    parse_field,
)
from automator.shared.clock import require_aware

FIELD_COUNT = 5
SEARCH_HORIZON_DAYS = 366 * 9


@dataclass(frozen=True)
class CronExpression:
    minutes: tuple[int, ...]
    hours: tuple[int, ...]
    days_of_month: frozenset[int]
    months: frozenset[int]
    days_of_week: frozenset[int]
    day_of_month_restricted: bool
    day_of_week_restricted: bool

    def matches_day(self, day: date) -> bool:
        if day.month not in self.months:
            return False
        by_month_day = day.day in self.days_of_month
        by_week_day = day.isoweekday() % 7 in self.days_of_week
        if self.day_of_month_restricted and self.day_of_week_restricted:
            return by_month_day or by_week_day
        if self.day_of_month_restricted:
            return by_month_day
        if self.day_of_week_restricted:
            return by_week_day
        return True


def parse_cron(text: str) -> CronExpression:
    parts = text.split()
    if len(parts) != FIELD_COUNT:
        raise CronSyntaxError(f"expected {FIELD_COUNT} fields, got {len(parts)}")
    minute, hour, day_of_month, month, day_of_week = parts
    weekdays = frozenset(value % 7 for value in parse_field(day_of_week, DAY_OF_WEEK))
    return CronExpression(
        minutes=tuple(sorted(parse_field(minute, MINUTE))),
        hours=tuple(sorted(parse_field(hour, HOUR))),
        days_of_month=parse_field(day_of_month, DAY_OF_MONTH),
        months=parse_field(month, MONTH),
        days_of_week=weekdays,
        day_of_month_restricted=not day_of_month.startswith("*"),
        day_of_week_restricted=not day_of_week.startswith("*"),
    )


def cron_error(text: str) -> str | None:
    try:
        parse_cron(text)
    except CronSyntaxError as error:
        return str(error)
    return None


def matching_days(expression: CronExpression, first: date) -> Iterator[date]:
    for offset in range(SEARCH_HORIZON_DAYS):
        day = first + timedelta(days=offset)
        if expression.matches_day(day):
            yield day


def wall_times(expression: CronExpression, day: date) -> Iterator[datetime]:
    for hour in expression.hours:
        for minute in expression.minutes:
            yield datetime(day.year, day.month, day.day, hour, minute)


def resolve_wall_time(wall: datetime, zone: ZoneInfo) -> datetime | None:
    instant = wall.replace(tzinfo=zone).astimezone(UTC)
    exists = instant.astimezone(zone).replace(tzinfo=None) == wall
    return instant if exists else None


def next_cron_time(expression: CronExpression, after: datetime, zone: ZoneInfo) -> datetime | None:
    moment = require_aware(after).astimezone(UTC)
    local = moment.astimezone(zone).replace(tzinfo=None, second=0, microsecond=0)
    earliest = local + timedelta(minutes=1)
    for day in matching_days(expression, earliest.date()):
        for wall in wall_times(expression, day):
            instant = resolve_wall_time(wall, zone) if wall >= earliest else None
            if instant is not None and instant > moment:
                return instant
    return None
