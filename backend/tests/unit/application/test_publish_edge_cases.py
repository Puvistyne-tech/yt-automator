from __future__ import annotations

import pytest

from autotube.domain.channels import ChannelDefaults
from autotube.domain.publish_plan import plan_uploads
from autotube.domain.run_enums import RunStatus, UploadStatus
from autotube.domain.youtube import ChannelAuth, UploadedVideo, VideoUpload
from autotube.shared.errors import NotFound, RuleConflict
from tests.fixtures.builders import add_channel, add_credential, target_input
from tests.fixtures.fake_pipeline import FakePipelineRegistry
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import approved_run, publish_run


def test_upload_error_without_message_is_named_by_its_class(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = approved_run(harness)

    def refuse(_auth: ChannelAuth, _video: VideoUpload) -> UploadedVideo:
        raise TimeoutError

    monkeypatch.setattr(harness.youtube, "upload_video", refuse)
    upload = publish_run(harness).execute(run.id).uploads[0]
    assert upload.status is UploadStatus.FAILED and upload.error == "TimeoutError"


@pytest.mark.parametrize("pipeline_type", ["fake_kids", "fake"])
def test_publish_with_an_unresolvable_pipeline_is_refused(
    harness: Harness, pipeline_type: str
) -> None:
    add_credential(harness)
    add_channel(harness, defaults=ChannelDefaults(made_for_kids=False))
    run = approved_run(
        harness, pipeline_type=pipeline_type, targets=(target_input(made_for_kids=None),)
    )
    harness.pipelines = FakePipelineRegistry([])
    with pytest.raises(RuleConflict, match=pipeline_type) as raised:
        publish_run(harness).execute(run.id)
    assert raised.value.code == "pipeline_missing"
    assert harness.youtube.uploads == []
    stored = harness.runs.get(run.id)
    assert stored is not None and stored.status is RunStatus.APPROVED


def test_publish_with_deleted_credential_is_not_found(harness: Harness) -> None:
    run = approved_run(harness)
    harness.credentials.delete("cred-1")
    with pytest.raises(NotFound):
        publish_run(harness).execute(run.id)
    assert harness.youtube.uploads == []


@pytest.mark.parametrize(("track_language", "sent"), [(None, "ta"), ("en", "en")])
def test_caption_language_falls_back_to_the_plan_language(
    harness: Harness, track_language: str | None, sent: str
) -> None:
    run = approved_run(harness, languages=("en", "ta"), targets=(target_input(language="ta"),))
    automation = harness.automations.get(run.automation_id)
    assert automation is not None
    channels = {"chan-1": harness.channels.list()[0]}
    descriptor = harness.pipeline.descriptor
    (plan,) = plan_uploads(run, automation.targets, channels, descriptor, harness.clock.now())
    track = next(a for a in run.artifacts if a.filename == "en.srt")
    plan = plan.model_copy(
        update={"captions": (track.model_copy(update={"language": track_language}),)}
    )
    assert harness.performer.perform(run.id, plan).status is UploadStatus.DONE
    assert harness.youtube.operations("upload_captions") == [f"vid-1:{sent}:en.srt"]
