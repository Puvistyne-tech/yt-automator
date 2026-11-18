from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from automator.domain.automations import Target
from automator.domain.channels import Privacy
from automator.domain.publish_time import (
    DELAY_OR_TIME,
    NEEDS_PUBLIC,
    publish_time_errors,
    scheduled_publish,
)

NOW = datetime(2026, 1, 5, 10, tzinfo=UTC)


def target(**fields: Any) -> Target:
    return Target(id="t1", channel_id="c1", language="en", variants=("landscape",), **fields)


@pytest.mark.parametrize(
    ("fields", "privacy", "expected"),
    [
        ({}, Privacy.PUBLIC, None),
        ({"publish_delay_minutes": 30}, Privacy.PUBLIC, NOW + timedelta(minutes=30)),
        ({"publish_time_of_day": "18:00"}, Privacy.PUBLIC, datetime(2026, 1, 5, 18, tzinfo=UTC)),
        ({"publish_time_of_day": "09:00"}, Privacy.PUBLIC, datetime(2026, 1, 6, 9, tzinfo=UTC)),
        (
            {"publish_time_of_day": "18:00", "publish_timezone": "Asia/Kolkata"},
            Privacy.PUBLIC,
            datetime(2026, 1, 5, 12, 30, tzinfo=UTC),
        ),
        ({"publish_time_of_day": "18:00"}, Privacy.PRIVATE, None),
        ({"publish_time_of_day": "18:00"}, Privacy.UNLISTED, None),
        ({"publish_time_of_day": "6pm"}, Privacy.PUBLIC, None),
        ({"publish_time_of_day": "18:00", "publish_timezone": "Mars/Base"}, Privacy.PUBLIC, None),
    ],
)
def test_scheduled_publish(
    fields: dict[str, Any], privacy: Privacy, expected: datetime | None
) -> None:
    assert scheduled_publish(target(**fields), privacy, NOW) == expected


def test_a_time_of_day_publish_in_the_spring_gap_moves_forward() -> None:
    gap = target(publish_time_of_day="02:30", publish_timezone="America/New_York")
    found = scheduled_publish(gap, Privacy.PUBLIC, datetime(2026, 3, 8, 6, tzinfo=UTC))
    assert found == datetime(2026, 3, 8, 7, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("fields", "errors"),
    [
        ({}, {}),
        ({"publish_time_of_day": "18:00"}, {}),
        ({"publish_time_of_day": "18:00", "privacy": Privacy.PUBLIC}, {}),
        (
            {"publish_time_of_day": "18:00", "publish_delay_minutes": 5},
            {"publish_time_of_day": DELAY_OR_TIME},
        ),
        (
            {"publish_time_of_day": "18:00", "privacy": Privacy.PRIVATE},
            {"publish_time_of_day": NEEDS_PUBLIC},
        ),
        (
            {"publish_time_of_day": "7"},
            {"publish_time_of_day": "'7' is not a time of day: use a 24-hour time such as 08:00"},
        ),
        ({"publish_timezone": "Mars/Base"}, {"publish_timezone": "unknown timezone 'Mars/Base'"}),
    ],
)
def test_publish_time_errors(fields: dict[str, Any], errors: dict[str, str]) -> None:
    assert publish_time_errors(target(**fields)) == errors


def test_targets_stored_before_publish_times_load_with_defaults() -> None:
    stored = Target.model_validate(
        {"id": "t1", "channel_id": "c1", "language": "en", "variants": ["landscape"]}
    )
    assert (stored.publish_time_of_day, stored.publish_timezone) == (None, "UTC")
