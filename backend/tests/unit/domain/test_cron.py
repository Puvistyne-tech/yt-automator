from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from autotube.domain.cron import cron_error, next_cron_time, parse_cron
from autotube.domain.cron_fields import CronSyntaxError

UTC_ZONE = ZoneInfo("UTC")


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


@pytest.mark.parametrize(
    ("expression", "minutes", "hours"),
    [
        ("* * * * *", tuple(range(60)), tuple(range(24))),
        ("*/15 0 * * *", (0, 15, 30, 45), (0,)),
        ("5,10-12 1-3/2 * * *", (5, 10, 11, 12), (1, 3)),
        ("30/10 9 * * *", (30, 40, 50), (9,)),
    ],
)
def test_parse_minute_and_hour_fields(
    expression: str, minutes: tuple[int, ...], hours: tuple[int, ...]
) -> None:
    parsed = parse_cron(expression)
    assert (parsed.minutes, parsed.hours) == (minutes, hours)


def test_parse_names_and_sunday_aliases() -> None:
    parsed = parse_cron("0 0 * jan-mar,DEC sun,7,MON")
    assert parsed.months == frozenset({1, 2, 3, 12})
    assert parsed.days_of_week == frozenset({0, 1})
    assert parsed.day_of_week_restricted and not parsed.day_of_month_restricted


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("* * * *", "expected 5 fields"),
        ("* * * * * *", "expected 5 fields"),
        ("60 * * * *", "outside 0-59"),
        ("* 24 * * *", "outside 0-23"),
        ("* * 0 * *", "outside 1-31"),
        ("* * * 13 *", "outside 1-12"),
        ("* * * * 8", "outside 0-7"),
        ("*/0 * * * *", "step"),
        ("5-1 * * * *", "backwards"),
        ("1,,2 * * * *", "empty list item"),
        ("a * * * *", "not a number"),
        ("* * * foo *", "not a number"),
    ],
)
def test_invalid_expressions_are_reported(expression: str, message: str) -> None:
    with pytest.raises(CronSyntaxError, match=message):
        parse_cron(expression)
    assert message in (cron_error(expression) or "")


def test_valid_expression_has_no_error() -> None:
    assert cron_error("0 9 * * 1-5") is None


@pytest.mark.parametrize(
    ("expression", "after", "expected"),
    [
        ("* * * * *", "2026-01-05T10:00:30", "2026-01-05T10:01:00"),
        ("0 9 * * *", "2026-01-05T08:59:00", "2026-01-05T09:00:00"),
        ("0 9 * * *", "2026-01-05T09:00:00", "2026-01-06T09:00:00"),
        ("30 18 * * 1-5", "2026-01-09T19:00:00", "2026-01-12T18:30:00"),
        ("0 0 1 * *", "2026-01-15T00:00:00", "2026-02-01T00:00:00"),
        ("0 0 31 * *", "2026-02-01T00:00:00", "2026-03-31T00:00:00"),
        ("0 0 29 2 *", "2026-01-01T00:00:00", "2028-02-29T00:00:00"),
        ("0 12 13 * 5", "2026-01-05T00:00:00", "2026-01-09T12:00:00"),
        ("0 0 * * 0", "2026-01-05T00:00:00", "2026-01-11T00:00:00"),
        ("59 23 31 12 *", "2026-12-31T23:59:00", "2027-12-31T23:59:00"),
    ],
)
def test_next_time_in_utc(expression: str, after: str, expected: str) -> None:
    assert next_cron_time(parse_cron(expression), utc(after), UTC_ZONE) == utc(expected)


def test_next_time_is_never_after_horizon_for_impossible_dates() -> None:
    assert next_cron_time(parse_cron("0 0 30 2 *"), utc("2026-01-01T00:00:00"), UTC_ZONE) is None


@pytest.mark.parametrize(
    ("zone", "after", "expected"),
    [
        ("Asia/Kolkata", "2026-01-05T00:00:00", "2026-01-05T03:30:00"),
        ("America/New_York", "2026-03-08T00:00:00", "2026-03-08T13:00:00"),
        ("America/New_York", "2026-03-07T00:00:00", "2026-03-07T14:00:00"),
    ],
)
def test_next_time_respects_zone_offsets(zone: str, after: str, expected: str) -> None:
    result = next_cron_time(parse_cron("0 9 * * *"), utc(after), ZoneInfo(zone))
    assert result == utc(expected)


def test_skipped_wall_time_during_spring_forward_is_not_fired() -> None:
    zone = ZoneInfo("America/New_York")
    result = next_cron_time(parse_cron("30 2 * * *"), utc("2026-03-08T05:00:00"), zone)
    assert result == utc("2026-03-09T06:30:00")


def test_repeated_wall_time_during_fall_back_fires_once() -> None:
    zone = ZoneInfo("America/New_York")
    expression = parse_cron("30 1 * * *")
    first = next_cron_time(expression, utc("2026-11-01T04:00:00"), zone)
    assert first == utc("2026-11-01T05:30:00")
    assert first is not None
    assert next_cron_time(expression, first, zone) == utc("2026-11-02T06:30:00")


def test_naive_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        next_cron_time(parse_cron("* * * * *"), datetime(2026, 1, 1), UTC_ZONE)
