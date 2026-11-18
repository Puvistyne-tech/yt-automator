from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

import pytest

from autotube.domain.local_times import (
    next_local_midnight,
    next_local_time,
    parse_time_of_day,
    time_of_day_errors,
    within_hours,
)

NEW_YORK = ZoneInfo("America/New_York")
KOLKATA = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize(
    ("text", "parsed"),
    [
        ("00:00", time(0, 0)),
        ("08:05", time(8, 5)),
        ("23:59", time(23, 59)),
        ("24:00", None),
        ("8:00", None),
        ("08:60", None),
        ("08:00:00", None),
        ("", None),
    ],
)
def test_parse_time_of_day(text: str, parsed: time | None) -> None:
    assert parse_time_of_day(text) == parsed


def test_time_of_day_errors_name_the_field() -> None:
    assert time_of_day_errors(None, "at") == {}
    assert time_of_day_errors("09:30", "at") == {}
    assert time_of_day_errors("9am", "at") == {
        "at": "'9am' is not a time of day: use a 24-hour time such as 08:00"
    }


@pytest.mark.parametrize(
    ("after", "at", "expected"),
    [
        (
            datetime(2026, 1, 5, 10, tzinfo=UTC),
            time(18, 0),
            datetime(2026, 1, 5, 12, 30, tzinfo=UTC),
        ),
        (
            datetime(2026, 1, 5, 13, tzinfo=UTC),
            time(18, 0),
            datetime(2026, 1, 6, 12, 30, tzinfo=UTC),
        ),
        (
            datetime(2026, 1, 5, 12, 30, tzinfo=UTC),
            time(18, 0),
            datetime(2026, 1, 6, 12, 30, tzinfo=UTC),
        ),
    ],
)
def test_next_local_time_is_strictly_after(after: datetime, at: time, expected: datetime) -> None:
    assert next_local_time(after, at, KOLKATA) == expected


def test_a_time_in_the_spring_gap_moves_forward_by_the_gap() -> None:
    after = datetime(2026, 3, 8, 5, 0, tzinfo=UTC)
    found = next_local_time(after, time(2, 30), NEW_YORK)
    assert found == datetime(2026, 3, 8, 7, 30, tzinfo=UTC)
    assert found.astimezone(NEW_YORK).time() == time(3, 30)


def test_a_time_in_the_autumn_overlap_uses_its_first_occurrence() -> None:
    after = datetime(2026, 11, 1, 4, 0, tzinfo=UTC)
    assert next_local_time(after, time(1, 30), NEW_YORK) == datetime(2026, 11, 1, 5, 30, tzinfo=UTC)


def test_the_second_occurrence_of_an_overlap_is_never_used() -> None:
    after = datetime(2026, 11, 1, 5, 45, tzinfo=UTC)
    assert next_local_time(after, time(1, 30), NEW_YORK) == datetime(2026, 11, 2, 6, 30, tzinfo=UTC)


def test_next_local_midnight_follows_the_zone() -> None:
    after = datetime(2026, 1, 5, 20, tzinfo=UTC)
    assert next_local_midnight(after, KOLKATA) == datetime(2026, 1, 6, 18, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("after", "midnight"),
    [
        (datetime(2026, 3, 8, 6, tzinfo=UTC), datetime(2026, 3, 9, 4, tzinfo=UTC)),
        (datetime(2026, 11, 1, 6, tzinfo=UTC), datetime(2026, 11, 2, 5, tzinfo=UTC)),
    ],
)
def test_next_local_midnight_spans_the_23_and_25_hour_days(
    after: datetime, midnight: datetime
) -> None:
    assert next_local_midnight(after, NEW_YORK) == midnight


@pytest.mark.parametrize(
    ("hour", "start", "end", "inside"),
    [
        (8, time(8), time(20), True),
        (19, time(8), time(20), True),
        (20, time(8), time(20), False),
        (7, time(8), time(20), False),
        (23, time(22), time(6), True),
        (5, time(22), time(6), True),
        (6, time(22), time(6), False),
        (12, time(22), time(6), False),
    ],
)
def test_within_hours(hour: int, start: time, end: time, inside: bool) -> None:
    moment = datetime(2026, 1, 5, hour, tzinfo=UTC)
    assert within_hours(moment, start, end, ZoneInfo("UTC")) is inside
