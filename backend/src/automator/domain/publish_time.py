from __future__ import annotations

from datetime import datetime, timedelta

from automator.domain.automations import TargetFields
from automator.domain.channels import Privacy
from automator.domain.local_times import next_local_time, parse_time_of_day, time_of_day_errors
from automator.domain.validation import timezone_errors
from automator.shared.clock import find_zone

DELAY_OR_TIME = "choose a publish delay or a time of day, not both"
NEEDS_PUBLIC = (
    "a publish time only applies to public videos: set privacy to Public or Channel default"
)
NOT_PUBLIC = frozenset({Privacy.PRIVATE, Privacy.UNLISTED})


def publish_time_errors(target: TargetFields) -> dict[str, str]:
    errors = timezone_errors(target.publish_timezone, "publish_timezone")
    if target.publish_time_of_day is None:
        return errors
    errors |= time_of_day_errors(target.publish_time_of_day, "publish_time_of_day")
    if target.publish_delay_minutes > 0:
        errors.setdefault("publish_time_of_day", DELAY_OR_TIME)
    if target.privacy in NOT_PUBLIC:
        errors.setdefault("publish_time_of_day", NEEDS_PUBLIC)
    return errors


def time_of_day_publish(target: TargetFields, now: datetime) -> datetime | None:
    at = parse_time_of_day(target.publish_time_of_day or "")
    zone = find_zone(target.publish_timezone)
    if at is None or zone is None:
        return None
    return next_local_time(now, at, zone)


def scheduled_publish(target: TargetFields, privacy: Privacy, now: datetime) -> datetime | None:
    if privacy is not Privacy.PUBLIC:
        return None
    if target.publish_time_of_day is not None:
        return time_of_day_publish(target, now)
    if target.publish_delay_minutes <= 0:
        return None
    return now + timedelta(minutes=target.publish_delay_minutes)
