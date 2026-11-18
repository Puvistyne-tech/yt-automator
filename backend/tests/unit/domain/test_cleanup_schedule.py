from __future__ import annotations

from datetime import timedelta

import pytest

from autotube.domain.retention import cleanup_due, working_files_removed_message
from autotube.domain.settings import AppSettingsInput
from tests.fixtures.fake_runtime import START


@pytest.mark.parametrize(
    ("last_hours", "now_hours", "interval", "due"),
    [
        (None, 0, 24, True),
        (0, 23.99, 24, False),
        (0, 24, 24, True),
        (None, 0, 0, False),
        (0, 1000, 0, False),
    ],
)
def test_the_cleanup_is_due_once_per_interval(
    last_hours: float | None, now_hours: float, interval: int, due: bool
) -> None:
    last = None if last_hours is None else START + timedelta(hours=last_hours)
    settings = AppSettingsInput(auto_cleanup_enabled=True, cleanup_interval_hours=interval)
    assert cleanup_due(last, START + timedelta(hours=now_hours), settings) is due


def test_the_cleanup_is_never_due_until_it_is_switched_on() -> None:
    assert AppSettingsInput().auto_cleanup_enabled is False
    assert not cleanup_due(None, START, AppSettingsInput(cleanup_interval_hours=1))


def test_the_working_files_message_names_the_size_in_megabytes() -> None:
    assert working_files_removed_message(2_500_000) == "Cleanup removed working files (2.5 MB)"
