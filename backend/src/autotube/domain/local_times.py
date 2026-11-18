from __future__ import annotations

import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from autotube.shared.clock import to_utc

TIME_OF_DAY = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
TIME_OF_DAY_HINT = "use a 24-hour time such as 08:00"


def parse_time_of_day(text: str) -> time | None:
    match = TIME_OF_DAY.match(text)
    return time(int(match[1]), int(match[2])) if match else None


def time_of_day_errors(text: str | None, field: str) -> dict[str, str]:
    if text is None or parse_time_of_day(text) is not None:
        return {}
    return {field: f"{text!r} is not a time of day: {TIME_OF_DAY_HINT}"}


def local_instant(day: date, at: time, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, at, tzinfo=zone).astimezone(UTC)


def next_local_time(after: datetime, at: time, zone: ZoneInfo) -> datetime:
    moment = to_utc(after)
    day = moment.astimezone(zone).date()
    today = local_instant(day, at, zone)
    return today if today > moment else local_instant(day + timedelta(days=1), at, zone)


def next_local_midnight(after: datetime, zone: ZoneInfo) -> datetime:
    day = to_utc(after).astimezone(zone).date()
    return local_instant(day + timedelta(days=1), time.min, zone)


def wall_time(moment: datetime, zone: ZoneInfo) -> time:
    return to_utc(moment).astimezone(zone).time()


def within_hours(moment: datetime, start: time, end: time, zone: ZoneInfo) -> bool:
    now = wall_time(moment, zone)
    if start < end:
        return start <= now < end
    return now >= start or now < end
