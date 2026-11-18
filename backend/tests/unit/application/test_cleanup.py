from __future__ import annotations

import logging

import pytest

from automator.domain.retention import CleanupAction
from automator.domain.run_enums import RunStatus
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import clean_up, preview_cleanup
from tests.unit.application.cleanup_support import (
    IMAGE_BYTES,
    VIDEO_BYTES,
    WORKSPACE_BYTES,
    after_days,
    keep,
    orphan,
    stored_run,
)

RUN_BYTES = VIDEO_BYTES + IMAGE_BYTES + WORKSPACE_BYTES
WORKING_BYTES = IMAGE_BYTES + WORKSPACE_BYTES


def three_ages(harness: Harness) -> None:
    keep(harness)
    stored_run(harness, "old")
    after_days(harness, 20)
    stored_run(harness, "middle", finished_at=harness.clock.now())
    after_days(harness, 28)
    stored_run(harness, "young", finished_at=harness.clock.now())
    stored_run(harness, "waiting", RunStatus.AWAITING_REVIEW)
    orphan(harness)
    after_days(harness, 30)


def test_the_preview_lists_what_would_go_and_removes_nothing(harness: Harness) -> None:
    three_ages(harness)
    report = preview_cleanup(harness).execute()
    assert report.dry_run and report.keep_runs_days == 30
    assert sorted((i.run_id, i.action, i.bytes) for i in report.items) == [
        ("middle", CleanupAction.REMOVE_INTERMEDIATE, WORKING_BYTES),
        ("old", CleanupAction.DELETE_RUN, RUN_BYTES),
        ("orphan-1", CleanupAction.REMOVE_ORPHAN, 9),
    ]
    assert report.total_bytes == WORKING_BYTES + RUN_BYTES + 9
    assert set(harness.runs.items) == {"old", "middle", "young", "waiting"}
    assert harness.files.run_ids() == {"old", "middle", "young", "waiting", "orphan-1"}


def test_cleanup_removes_expired_runs_working_files_and_stray_folders(
    harness: Harness, caplog: pytest.LogCaptureFixture
) -> None:
    three_ages(harness)
    with caplog.at_level(logging.INFO, logger="automator"):
        report = clean_up(harness).execute()
    assert not report.dry_run and report.total_bytes == WORKING_BYTES + RUN_BYTES + 9
    assert set(harness.runs.items) == {"middle", "young", "waiting"}
    assert harness.files.run_ids() == {"middle", "young", "waiting"}
    middle = harness.runs.items["middle"]
    assert [a.id for a in middle.artifacts] == ["middle-v"]
    assert middle.intermediate_removed_at == harness.clock.now()
    assert "Cleanup removed working files" in middle.logs[-1].message
    assert harness.files.usage("middle", frozenset({"middle-v"})).intermediate_bytes == 0
    assert "deleted run old" in caplog.text and "removed folder orphan-1" in caplog.text


def test_a_second_cleanup_finds_nothing_left(harness: Harness) -> None:
    three_ages(harness)
    clean_up(harness).execute()
    again = clean_up(harness).execute()
    assert again.items == () and again.total_bytes == 0


def test_a_crash_after_deleting_the_row_leaves_a_folder_the_next_pass_removes(
    harness: Harness,
) -> None:
    keep(harness)
    stored_run(harness, "old")
    after_days(harness, 30)
    harness.files.fail_for("old")
    assert clean_up(harness).execute().items == ()
    assert "old" not in harness.runs.items and "old" in harness.files.run_ids()
    preview = preview_cleanup(harness).execute()
    assert [(i.run_id, i.action) for i in preview.items] == [("old", CleanupAction.REMOVE_ORPHAN)]
    harness.files.failing.clear()
    healed = clean_up(harness).execute()
    assert healed.total_bytes == RUN_BYTES and harness.files.run_ids() == frozenset()


def test_a_crash_after_marking_working_files_is_finished_by_the_next_pass(
    harness: Harness,
) -> None:
    keep(harness)
    stored_run(harness, "aged")
    after_days(harness, 8)
    harness.files.fail_for("aged")
    clean_up(harness).execute()
    marked = harness.runs.items["aged"]
    assert marked.intermediate_removed_at is not None and len(marked.artifacts) == 1
    harness.files.failing.clear()
    healed = clean_up(harness).execute()
    assert [(i.action, i.bytes) for i in healed.items] == [
        (CleanupAction.REMOVE_INTERMEDIATE, WORKING_BYTES)
    ]
    assert harness.runs.items["aged"].intermediate_removed_at == marked.intermediate_removed_at


def test_a_run_retried_after_the_plan_is_left_alone(harness: Harness) -> None:
    keep(harness)
    stored_run(harness, "old")
    stored_run(harness, "aged", finished_at=None)
    after_days(harness, 30)
    cleaner = clean_up(harness)
    plan = cleaner.planner.plan()
    for run_id in ("old", "aged"):
        harness.runs.save(harness.runs.items[run_id].model_copy(update={"status": "queued"}))
    assert [cleaner.attempt(plan, item) for item in plan.items] == [None, None]
    assert set(harness.runs.items) == {"old", "aged"}
    assert harness.files.usage("old", frozenset()).total_bytes == RUN_BYTES


def test_a_folder_whose_run_appears_after_the_plan_is_kept(harness: Harness) -> None:
    orphan(harness, "late")
    cleaner = clean_up(harness)
    plan = cleaner.planner.plan()
    stored_run(harness, "late", RunStatus.QUEUED)
    assert cleaner.attempt(plan, plan.items[0]) is None
    assert "late" in harness.files.run_ids()


def test_zero_days_keeps_everything(harness: Harness) -> None:
    keep(harness, runs=0, intermediate=0)
    stored_run(harness, "ancient")
    after_days(harness, 5000)
    assert clean_up(harness).execute().items == ()
    assert "ancient" in harness.runs.items
