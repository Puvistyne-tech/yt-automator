from __future__ import annotations

from datetime import timedelta

import pytest

from automator.application.scheduled_cleanup import ScheduledCleanup
from automator.domain.channels import Privacy
from automator.domain.run_enums import RunStatus, StageStatus
from automator.domain.settings import AppSettingsInput
from automator.shared.errors import RuleConflict
from tests.fixtures.builders import target_input
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import (
    approved_run,
    clean_up,
    failed_at_render,
    get_storage,
    publish_run,
    retry_run,
)
from tests.unit.application.cleanup_support import (
    IMAGE_BYTES,
    VIDEO_BYTES,
    WORKSPACE_BYTES,
    keep,
    orphan,
    stored_run,
)


def scheduled(harness: Harness, interval: int, enabled: bool = True) -> ScheduledCleanup:
    harness.app_settings.stored = AppSettingsInput(
        keep_runs_days=30, auto_cleanup_enabled=enabled, cleanup_interval_hours=interval
    )
    return ScheduledCleanup(clean_up(harness), harness.app_settings)


def test_the_scheduled_cleanup_deletes_nothing_until_it_is_switched_on(harness: Harness) -> None:
    stored_run(harness, "old")
    orphan(harness)
    harness.clock.advance(days=400)
    job = scheduled(harness, interval=1, enabled=False)
    assert job.execute(harness.clock.now()) is None and job.last_ran is None
    assert "old" in harness.runs.items and "orphan-1" in harness.files.run_ids()
    assert [i.run_id for i in clean_up(harness).execute().items] == ["old", "orphan-1"]


def test_the_scheduled_cleanup_runs_once_per_interval(harness: Harness) -> None:
    job = scheduled(harness, interval=6)
    start = harness.clock.now()
    assert job.execute(start) is not None
    assert job.execute(start + timedelta(hours=5, minutes=59)) is None
    assert job.execute(start + timedelta(hours=6)) is not None
    assert job.last_ran == start + timedelta(hours=6)


def test_an_interval_of_zero_never_cleans_up_on_its_own(harness: Harness) -> None:
    job = scheduled(harness, interval=0)
    assert job.execute(harness.clock.now()) is None and job.last_ran is None


def test_storage_reports_finals_working_files_strays_and_free_space(harness: Harness) -> None:
    stored_run(harness, "r1")
    stored_run(harness, "r2", automation_id="auto-2", automation_name="Shorts")
    orphan(harness, size=9)
    report = get_storage(harness).execute()
    assert report.final_bytes == 2 * VIDEO_BYTES
    assert report.intermediate_bytes == 2 * (IMAGE_BYTES + WORKSPACE_BYTES)
    assert report.orphan_bytes == 9 and report.free_bytes == 5_000_000
    assert {u.automation_id for u in report.automations} == {"auto-1", "auto-2"}


def pruned_failed_run(harness: Harness) -> str:
    failed = failed_at_render(harness)
    keep(harness)
    harness.clock.advance(days=8)
    clean_up(harness).execute()
    assert harness.runs.items[failed.id].intermediate_removed_at is not None
    return failed.id


def test_a_retry_after_working_files_were_removed_starts_from_the_first_stage(
    harness: Harness,
) -> None:
    run_id = pruned_failed_run(harness)
    retried = retry_run(harness).execute(run_id)
    assert all(stage.status is StageStatus.PENDING for stage in retried.stages)
    assert retried.intermediate_removed_at is None


def test_a_retry_from_a_later_stage_is_refused_once_working_files_are_gone(
    harness: Harness,
) -> None:
    run_id = pruned_failed_run(harness)
    with pytest.raises(RuleConflict) as raised:
        retry_run(harness).execute(run_id, from_stage="render")
    assert raised.value.code == "intermediate_files_removed"
    first = harness.runs.items[run_id].stages[0].stage_id
    assert retry_run(harness).execute(run_id, from_stage=first).status is RunStatus.QUEUED


def test_a_delayed_public_upload_records_when_it_goes_public(harness: Harness) -> None:
    target = target_input(privacy=Privacy.PUBLIC, publish_delay_minutes=90)
    run = approved_run(harness, targets=(target,))
    published = publish_run(harness).execute(run.id)
    assert published.uploads[0].publish_at == harness.clock.now() + timedelta(minutes=90)
