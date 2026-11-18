from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def utc_now() -> datetime:
    return datetime.now(UTC)


def require_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return moment


def to_utc(moment: datetime) -> datetime:
    return require_aware(moment).astimezone(UTC)


def to_iso(moment: datetime) -> str:
    return to_utc(moment).isoformat()


def find_zone(name: str) -> ZoneInfo | None:
    if not name:
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def is_valid_timezone(name: str) -> bool:
    return find_zone(name) is not None


def local_date(moment: datetime, zone_name: str) -> date:
    return to_utc(moment).astimezone(ZoneInfo(zone_name)).date()


def local_day_start(moment: datetime, zone_name: str) -> datetime:
    zone = ZoneInfo(zone_name)
    start = datetime.combine(local_date(moment, zone_name), time.min, tzinfo=zone)
    return start.astimezone(UTC)
