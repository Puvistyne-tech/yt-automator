from __future__ import annotations

import pytest

from autotube.domain.channels import channel_token_secret_name
from autotube.domain.run_enums import RunEventKind, RunStatus, UploadStatus
from autotube.shared.errors import RuleConflict
from tests.fixtures.builders import add_channel, finished_run, target_input
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import approved_run, publish_run

BOTH = ("landscape", "short")


def used_units(harness: Harness) -> int:
    return sum(harness.ledger.units.values())


def test_publish_uploads_each_target_variant_with_extras(harness: Harness) -> None:
    run = approved_run(
        harness,
        languages=("en", "ta"),
        targets=(
            target_input(variants=BOTH, playlist_id="PL-1"),
            target_input(language="ta"),
        ),
    )
    published = publish_run(harness).execute(run.id)
    assert published.status is RunStatus.PUBLISHED and published.error is None
    assert [(u.language, u.variant, u.status) for u in published.uploads] == [
        ("en", "landscape", UploadStatus.DONE),
        ("en", "short", UploadStatus.DONE),
        ("ta", "landscape", UploadStatus.DONE),
    ]
    assert harness.youtube.operations("upload_video") == [
        "en-landscape.mp4",
        "en-short.mp4",
        "ta-landscape.mp4",
    ]
    assert harness.youtube.operations("set_thumbnail") == [
        "vid-1:en-landscape.png",
        "vid-2:en-short.png",
        "vid-3:ta-landscape.png",
    ]
    assert harness.youtube.operations("upload_captions") == [
        "vid-1:en:en.srt",
        "vid-2:en:en.srt",
        "vid-3:ta:ta.srt",
    ]
    assert harness.youtube.operations("add_to_playlist") == ["vid-1:PL-1", "vid-2:PL-1"]
    assert [u.quota_units for u in published.uploads] == [2100, 2100, 2050]
    assert used_units(harness) == 6250
    assert published.uploads[0].url == "https://youtu.be/vid-1"


def test_upload_request_uses_metadata_and_safe_defaults(harness: Harness) -> None:
    publish_run(harness).execute(approved_run(harness).id)
    video = harness.youtube.uploads[0]
    assert (video.title, video.description, video.tags) == ("Story in en", "A story", ("kids",))
    assert video.privacy.value == "private" and video.made_for_kids is False
    assert video.publish_at is None and video.default_language == "en"


def test_pipeline_category_language_and_hashtags_reach_the_upload(harness: Harness) -> None:
    extras = {"category_id": "27", "default_language": "ta", "hashtags": ["#A"]}
    run = approved_run(harness, settings={"extra_meta": extras})
    publish_run(harness).execute(run.id)
    video = harness.youtube.uploads[0]
    assert (video.category_id, video.default_language) == ("27", "ta")
    assert video.description == "A story\n\n#A"


def test_channel_defaults_fill_what_the_metadata_leaves_out(harness: Harness) -> None:
    publish_run(harness).execute(approved_run(harness).id)
    video = harness.youtube.uploads[0]
    assert (video.category_id, video.description) == ("22", "A story")


def test_kids_pipeline_uploads_are_made_for_kids(harness: Harness) -> None:
    publish_run(harness).execute(approved_run(harness, pipeline_type="fake_kids").id)
    assert harness.youtube.uploads[0].made_for_kids is True


def test_failed_upload_fails_only_itself(harness: Harness) -> None:
    harness.youtube.failing_videos = {"en-short.mp4"}
    published = publish_run(harness).execute(
        approved_run(harness, targets=(target_input(variants=BOTH),)).id
    )
    assert published.status is RunStatus.PUBLISHED
    assert [u.status for u in published.uploads] == [UploadStatus.DONE, UploadStatus.FAILED]
    assert published.uploads[1].error == "upload of en-short.mp4 rejected"
    assert published.uploads[1].quota_units == 1600


def test_all_uploads_failing_returns_run_to_approved(harness: Harness) -> None:
    harness.youtube.failing_videos = {"en-landscape.mp4"}
    run = approved_run(harness)
    result = publish_run(harness).execute(run.id)
    assert result.status is RunStatus.APPROVED and result.error == "no upload succeeded"
    harness.youtube.failing_videos = set()
    assert publish_run(harness).execute(run.id).status is RunStatus.PUBLISHED


@pytest.mark.parametrize("operation", ["set_thumbnail", "upload_captions", "add_to_playlist"])
def test_secondary_failures_keep_the_upload_done(harness: Harness, operation: str) -> None:
    harness.youtube.failing_operations = {operation}
    run = approved_run(harness, targets=(target_input(playlist_id="PL-1"),))
    upload = publish_run(harness).execute(run.id).uploads[0]
    assert upload.status is UploadStatus.DONE
    assert upload.error is not None and f"{operation} rejected" in upload.error


def test_missing_channel_token_fails_that_upload(harness: Harness) -> None:
    add_channel(harness, channel_id="chan-2", token=None)
    run = approved_run(harness, targets=(target_input(), target_input(channel_id="chan-2")))
    assert not harness.secrets.has(channel_token_secret_name("chan-2"))
    result = publish_run(harness).execute(run.id)
    assert [u.status for u in result.uploads] == [UploadStatus.DONE, UploadStatus.FAILED]
    assert "no stored authorization" in (result.uploads[1].error or "")


def test_targets_without_video_are_skipped(harness: Harness) -> None:
    run = approved_run(harness, targets=(target_input(variants=BOTH),))
    kept = tuple(a for a in run.artifacts if a.filename != "en-short.mp4")
    harness.runs.save(run.model_copy(update={"artifacts": kept}))
    result = publish_run(harness).execute(run.id)
    assert [u.status for u in result.uploads] == [UploadStatus.DONE, UploadStatus.SKIPPED]
    assert "no video" in (result.uploads[1].error or "")
    assert harness.youtube.operations("upload_video") == ["en-landscape.mp4"]


def test_runs_without_thumbnail_do_not_set_one(harness: Harness) -> None:
    result = publish_run(harness).execute(
        approved_run(harness, settings={"with_thumbnail": False}).id
    )
    assert harness.youtube.operations("set_thumbnail") == []
    assert result.uploads[0].quota_units == 2000


@pytest.mark.parametrize("status", [RunStatus.AWAITING_REVIEW, RunStatus.FAILED, RunStatus.QUEUED])
def test_only_approved_runs_publish(harness: Harness, status: RunStatus) -> None:
    run = finished_run(harness).model_copy(update={"status": status})
    harness.runs.save(run)
    with pytest.raises(RuleConflict):
        publish_run(harness).execute(run.id)
    assert harness.youtube.uploads == []


def test_publish_refuses_when_quota_is_too_low(harness: Harness) -> None:
    run = approved_run(harness)
    day = harness.quota_report.today()
    harness.ledger.record("cred-1", 10000 - 2049, day)
    with pytest.raises(RuleConflict) as raised:
        publish_run(harness).execute(run.id)
    assert raised.value.code == "quota_exceeded"
    assert harness.youtube.uploads == []
    harness.ledger.units[("cred-1", day)] -= 1
    assert publish_run(harness).execute(run.id).status is RunStatus.PUBLISHED


def test_publish_requires_automation_and_publishable_targets(harness: Harness) -> None:
    run = approved_run(harness)
    harness.automations.delete(run.automation_id)
    with pytest.raises(RuleConflict) as raised:
        publish_run(harness).execute(run.id)
    assert raised.value.code == "automation_deleted"
    other = approved_run(harness, targets=())
    with pytest.raises(RuleConflict) as nothing:
        publish_run(harness).execute(other.id)
    assert nothing.value.code == "nothing_to_publish"


def test_publish_emits_upload_events(harness: Harness) -> None:
    run = publish_run(harness).execute(approved_run(harness).id)
    statuses = [
        e.payload["status"]
        for e in harness.events.published
        if e.run_id == run.id and e.kind is RunEventKind.UPLOAD
    ]
    assert statuses == ["uploading", "done"]
