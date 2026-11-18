from __future__ import annotations

from datetime import timedelta

import pytest

from autotube.domain.automations import TargetFields
from autotube.domain.channels import Privacy
from autotube.domain.retention import (
    CleanupAction,
    CleanupItem,
    RetentionPolicy,
    cleanup_action,
    cleanup_report,
    final_artifact_ids,
    has_intermediate_work,
    is_final_output,
    retention_policy,
    without_intermediate,
)
from autotube.domain.run_enums import ArtifactKind, RunStatus, UploadStatus
from autotube.domain.settings import AppSettingsInput
from tests.fixtures.retention_data import artifact, days_later, finished, upload
from tests.unit.infrastructure.records import run

POLICY = RetentionPolicy(keep_runs_days=30, keep_intermediate_days=7)


@pytest.mark.parametrize(
    "status",
    [
        RunStatus.QUEUED,
        RunStatus.RUNNING,
        RunStatus.AWAITING_REVIEW,
        RunStatus.APPROVED,
        RunStatus.PUBLISHING,
    ],
)
def test_unfinished_and_unpublished_runs_are_never_touched(status: RunStatus) -> None:
    assert cleanup_action(finished(status), days_later(400), POLICY) is None


@pytest.mark.parametrize(
    "status", [RunStatus.PUBLISHED, RunStatus.REJECTED, RunStatus.FAILED, RunStatus.CANCELLED]
)
def test_finished_runs_expire_after_keep_runs_days(status: RunStatus) -> None:
    assert cleanup_action(finished(status), days_later(30), POLICY) is CleanupAction.DELETE_RUN


def test_the_run_boundary_is_inclusive_to_the_second() -> None:
    almost = days_later(30) - timedelta(seconds=1)
    assert cleanup_action(finished(), almost, POLICY) is CleanupAction.REMOVE_INTERMEDIATE
    assert cleanup_action(finished(), days_later(30), POLICY) is CleanupAction.DELETE_RUN


def test_the_working_files_boundary_comes_first() -> None:
    almost = days_later(7) - timedelta(seconds=1)
    assert cleanup_action(finished(), almost, POLICY) is None
    assert cleanup_action(finished(), days_later(7), POLICY) is CleanupAction.REMOVE_INTERMEDIATE


def test_zero_keeps_runs_and_working_files_forever() -> None:
    assert cleanup_action(finished(), days_later(4000), RetentionPolicy()) is None
    keep_runs = RetentionPolicy(keep_intermediate_days=1)
    assert cleanup_action(finished(), days_later(4000), keep_runs) is (
        CleanupAction.REMOVE_INTERMEDIATE
    )


def test_a_run_without_finish_time_ages_from_its_creation() -> None:
    created = run("r1", status=RunStatus.CANCELLED, finished_at=None)
    later = created.created_at + timedelta(days=30)
    assert cleanup_action(created, later, POLICY) is CleanupAction.DELETE_RUN


@pytest.mark.parametrize("status", [UploadStatus.PENDING, UploadStatus.UPLOADING])
def test_a_pending_upload_protects_the_run(status: UploadStatus) -> None:
    pending = finished(uploads=(upload(status=status),))
    assert cleanup_action(pending, days_later(400), POLICY) is None


def test_a_scheduled_upload_protects_the_run_until_it_goes_public() -> None:
    public_at = days_later(60)
    scheduled = finished(uploads=(upload(status=UploadStatus.DONE, publish_at=public_at),))
    almost = public_at - timedelta(seconds=1)
    assert cleanup_action(scheduled, almost, POLICY) is None
    assert cleanup_action(scheduled, public_at, POLICY) is CleanupAction.DELETE_RUN


def test_done_failed_and_skipped_uploads_do_not_protect() -> None:
    statuses = (UploadStatus.DONE, UploadStatus.FAILED, UploadStatus.SKIPPED)
    uploads = tuple(upload(status=s, privacy=Privacy.PRIVATE) for s in statuses)
    assert cleanup_action(finished(uploads=uploads), days_later(30), POLICY) is (
        CleanupAction.DELETE_RUN
    )


def test_a_failed_run_waiting_for_an_automatic_retry_is_never_touched() -> None:
    waiting = finished(RunStatus.FAILED, retry_at=days_later(500))
    assert cleanup_action(waiting, days_later(400), POLICY) is None
    given_up = waiting.model_copy(update={"retry_at": None})
    assert cleanup_action(given_up, days_later(400), POLICY) is CleanupAction.DELETE_RUN


def test_final_outputs_are_videos_thumbnails_captions_and_metadata_with_a_language() -> None:
    finals = [artifact(k.value, k) for k in ArtifactKind]
    assert [a.id for a in finals if is_final_output(a)] == [
        "video",
        "subtitle",
        "thumbnail",
        "metadata",
    ]
    assert not is_final_output(artifact("story", ArtifactKind.METADATA, language=None))


def test_removing_working_files_keeps_finals_and_the_first_removal_time() -> None:
    video, image = artifact("v", ArtifactKind.VIDEO), artifact("i", ArtifactKind.IMAGE)
    pruned = without_intermediate(finished(artifacts=(video, image)), days_later(8))
    assert pruned.artifacts == (video,) and pruned.intermediate_removed_at == days_later(8)
    again = without_intermediate(pruned, days_later(9))
    assert again.intermediate_removed_at == days_later(8)
    assert final_artifact_ids(pruned) == frozenset({"v"})


def test_working_files_are_pending_while_listed_or_on_disk() -> None:
    video, image = artifact("v", ArtifactKind.VIDEO), artifact("i", ArtifactKind.IMAGE)
    assert has_intermediate_work(finished(artifacts=(video, image)), 0)
    assert has_intermediate_work(finished(artifacts=(video,)), 5)
    assert not has_intermediate_work(finished(artifacts=(video,)), 0)


def test_the_policy_comes_from_the_app_settings() -> None:
    settings = AppSettingsInput(keep_runs_days=10, keep_intermediate_days=2)
    target = TargetFields(channel_id="c", language="en", variants=("v",))
    assert retention_policy(settings, {"t": target}) == RetentionPolicy(
        keep_runs_days=10, keep_intermediate_days=2, publish_targets={"t": target}
    )


def test_a_report_totals_its_items() -> None:
    items = [
        CleanupItem(run_id="a", action=CleanupAction.DELETE_RUN, bytes=5),
        CleanupItem(run_id="b", action=CleanupAction.REMOVE_ORPHAN, bytes=7),
    ]
    report = cleanup_report(items, POLICY, dry_run=True)
    assert (report.total_bytes, report.dry_run, report.keep_runs_days) == (12, True, 30)
