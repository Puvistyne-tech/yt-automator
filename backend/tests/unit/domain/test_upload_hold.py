from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from autotube.domain.automations import TargetFields
from autotube.domain.channels import Privacy
from autotube.domain.retention import CleanupAction, RetentionPolicy, cleanup_action
from autotube.domain.run_enums import UploadStatus
from autotube.domain.run_parts import Upload
from autotube.domain.upload_hold import holds_run
from tests.fixtures.retention_data import days_later, finished, upload

DAY_MINUTES = 24 * 60
LEGACY_TARGET = "t-old"


def policy(**target: Any) -> RetentionPolicy:
    rule = TargetFields(channel_id="c", language="en", variants=("v",), **target)
    return RetentionPolicy(keep_runs_days=30, publish_targets={LEGACY_TARGET: rule})


def legacy_upload(privacy: Privacy | None) -> Upload:
    return upload(status=UploadStatus.DONE, privacy=privacy, target_id=LEGACY_TARGET)


@pytest.mark.parametrize("privacy", [Privacy.PUBLIC, None])
def test_an_older_upload_is_held_for_its_target_publish_delay(privacy: Privacy | None) -> None:
    rules = policy(publish_delay_minutes=60 * DAY_MINUTES)
    held = finished(uploads=(legacy_upload(privacy),))
    assert cleanup_action(held, days_later(60) - timedelta(seconds=1), rules) is None
    assert cleanup_action(held, days_later(60), rules) is CleanupAction.DELETE_RUN


def test_an_older_upload_is_held_until_its_target_time_of_day_after_finishing() -> None:
    finished_late = datetime(2026, 1, 5, 23, 0, tzinfo=UTC)
    release = datetime(2026, 1, 6, 6, 30, tzinfo=UTC)
    targets = policy(publish_time_of_day="06:30", publish_timezone="UTC").publish_targets
    legacy = legacy_upload(Privacy.PUBLIC)
    assert holds_run(legacy, finished_late, release - timedelta(seconds=1), targets)
    assert not holds_run(legacy, finished_late, release, targets)


def test_an_older_upload_is_held_when_its_release_time_cannot_be_known() -> None:
    held = finished(uploads=(legacy_upload(Privacy.PUBLIC),))
    assert cleanup_action(held, days_later(4000), RetentionPolicy(keep_runs_days=30)) is None
    unknown_zone = policy(publish_time_of_day="06:30", publish_timezone="Mars/Base")
    assert cleanup_action(held, days_later(4000), unknown_zone) is None


@pytest.mark.parametrize("privacy", [Privacy.PRIVATE, Privacy.UNLISTED])
def test_an_upload_that_never_goes_public_does_not_hold(privacy: Privacy) -> None:
    kept_private = finished(uploads=(legacy_upload(privacy),))
    assert cleanup_action(kept_private, days_later(30), policy()) is CleanupAction.DELETE_RUN


def test_a_recorded_publish_time_wins_over_the_target_rule() -> None:
    recorded = upload(status=UploadStatus.DONE, privacy=Privacy.PUBLIC, publish_at=days_later(45))
    held = finished(uploads=(recorded.model_copy(update={"target_id": LEGACY_TARGET}),))
    assert cleanup_action(held, days_later(44), policy()) is None
    assert cleanup_action(held, days_later(45), policy()) is CleanupAction.DELETE_RUN
