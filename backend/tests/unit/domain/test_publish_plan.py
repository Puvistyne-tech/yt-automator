from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from automator.domain.artifact_selection import best_artifact, caption_tracks, video_metadata
from automator.domain.automations import Target
from automator.domain.channels import Channel, ChannelDefaults, Privacy
from automator.domain.model_base import JsonObject
from automator.domain.publish_plan import plan_uploads, quota_needed
from automator.domain.quota import QuotaPolicy
from automator.domain.run_enums import ArtifactKind, UploadStatus
from automator.domain.run_parts import Artifact
from automator.domain.runs import Run
from tests.fixtures.fake_pipeline import FakePipeline, kids_pipeline

NOW = datetime(2026, 1, 5, 10, tzinfo=UTC)


def artifact(
    kind: ArtifactKind, language: str | None, variant: str | None, meta: JsonObject | None = None
) -> Artifact:
    name = f"{kind.value}-{language}-{variant}"
    return Artifact(
        id=name,
        kind=kind,
        stage_id="render",
        language=language,
        variant=variant,
        filename=name,
        media_type="x/y",
        size_bytes=1,
        meta=meta or {},
    )


ARTIFACTS = (
    artifact(ArtifactKind.VIDEO, "en", "landscape"),
    artifact(ArtifactKind.VIDEO, "en", "short"),
    artifact(ArtifactKind.VIDEO, "ta", "landscape"),
    artifact(ArtifactKind.THUMBNAIL, "en", None),
    artifact(ArtifactKind.THUMBNAIL, "en", "short"),
    artifact(ArtifactKind.SUBTITLE, "en", None),
    artifact(ArtifactKind.SUBTITLE, "ta", None),
    artifact(ArtifactKind.METADATA, "en", None, {"title": "Owls", "tags": ["a", 1]}),
)


def make_run(languages: tuple[str, ...] = ("en", "ta")) -> Run:
    return Run(
        id="r1",
        automation_id="a1",
        automation_name="Bedtime",
        pipeline_type="fake",
        languages=languages,
        settings_snapshot={},
        artifacts=ARTIFACTS,
        created_at=NOW,
    )


def target(**overrides: Any) -> Target:
    fields: dict[str, Any] = {
        "id": "t1",
        "channel_id": "c1",
        "language": "en",
        "variants": ("landscape",),
    }
    return Target(**(fields | overrides))


CHANNEL = Channel(
    id="c1",
    credential_id="cred",
    youtube_channel_id="UC1",
    title="C",
    defaults=ChannelDefaults(privacy=Privacy.PUBLIC),
    connected_at=NOW,
)
DESCRIPTOR = FakePipeline().descriptor


def plans(*targets: Target, languages: tuple[str, ...] = ("en", "ta")) -> list[Any]:
    return plan_uploads(make_run(languages), targets, {"c1": CHANNEL}, DESCRIPTOR, NOW)


def test_one_plan_per_target_and_variant() -> None:
    result = plans(target(variants=("landscape", "short")), target(id="t2", language="ta"))
    assert [(p.target.id, p.language, p.variant) for p in result] == [
        ("t1", "en", "landscape"),
        ("t1", "en", "short"),
        ("t2", "ta", "landscape"),
    ]


def test_targets_outside_run_languages_are_skipped_without_cost() -> None:
    (plan,) = plans(target(language="ta"), languages=("en",))
    assert plan.skip_reason == "language 'ta' is not in this run"
    upload = plan.initial_upload()
    assert upload.status is UploadStatus.SKIPPED and upload.error == plan.skip_reason
    assert plan.cost(QuotaPolicy()) == 0


def test_plan_picks_artifacts_and_metadata() -> None:
    landscape, short = plans(target(variants=("landscape", "short")))
    assert landscape.video is not None and landscape.video.id == "video-en-landscape"
    assert landscape.thumbnail is not None and landscape.thumbnail.id == "thumbnail-en-None"
    assert short.thumbnail is not None and short.thumbnail.id == "thumbnail-en-short"
    assert [c.id for c in landscape.captions] == ["subtitle-en-None"]
    assert landscape.metadata.title == "Owls" and landscape.metadata.tags == ("a", "1")


def test_missing_video_or_channel_is_skipped_without_cost() -> None:
    no_video = plans(target(id="t2", language="ta", variants=("short",)))[0]
    ghost = plans(target(channel_id="ghost"))[0]
    assert "no video" in (no_video.skip_reason or "")
    assert "no longer exists" in (ghost.skip_reason or "")
    assert ghost.initial_upload().status is UploadStatus.SKIPPED
    assert no_video.cost(QuotaPolicy()) == 0


def test_quota_needed_sums_per_credential() -> None:
    result = plans(target(variants=("landscape", "short"), playlist_id="PL"))
    assert quota_needed(result, QuotaPolicy()) == {"cred": (1600 + 50 + 400 + 50) * 2}


@pytest.mark.parametrize(
    ("privacy", "delay", "publish_at"),
    [
        (None, 0, None),
        (None, 30, NOW + timedelta(minutes=30)),
        (Privacy.UNLISTED, 30, None),
        (Privacy.PRIVATE, 30, None),
    ],
)
def test_scheduled_publish_only_for_public_targets(
    privacy: Privacy | None, delay: int, publish_at: datetime | None
) -> None:
    plan = plans(target(privacy=privacy, publish_delay_minutes=delay))[0]
    assert plan.publish_at == publish_at
    assert plan.initial_upload().publish_at == publish_at


def test_kids_pipeline_plans_are_made_for_kids() -> None:
    run = make_run()
    regular = plan_uploads(run, [target(made_for_kids=False)], {"c1": CHANNEL}, DESCRIPTOR, NOW)
    kids = plan_uploads(
        run, [target(made_for_kids=False)], {"c1": CHANNEL}, kids_pipeline().descriptor, NOW
    )
    assert (regular[0].made_for_kids, kids[0].made_for_kids) == (False, True)


def test_initial_upload_records_the_effective_privacy_and_made_for_kids() -> None:
    inherited, overridden = plans(
        target(), target(id="t2", privacy=Privacy.UNLISTED, made_for_kids=True)
    )
    first, second = inherited.initial_upload(), overridden.initial_upload()
    assert (first.privacy, first.made_for_kids) == (Privacy.PUBLIC, False)
    assert (second.privacy, second.made_for_kids) == (Privacy.UNLISTED, True)


def test_a_skipped_upload_still_records_its_effective_audience() -> None:
    (plan,) = plans(target(language="ta", privacy=Privacy.UNLISTED), languages=("en",))
    upload = plan.initial_upload()
    assert upload.status is UploadStatus.SKIPPED
    assert (upload.privacy, upload.made_for_kids) == (Privacy.UNLISTED, False)


def test_kids_pipeline_uploads_are_recorded_as_made_for_kids() -> None:
    (plan,) = plan_uploads(
        make_run(), [target(made_for_kids=False)], {"c1": CHANNEL}, kids_pipeline().descriptor, NOW
    )
    assert plan.initial_upload().made_for_kids is True


def test_metadata_falls_back_to_automation_name() -> None:
    assert video_metadata(ARTIFACTS, "ta", "landscape", "Bedtime").title == "Bedtime"


def test_best_artifact_prefers_exact_then_generic_and_rejects_mismatch() -> None:
    assert best_artifact(ARTIFACTS, ArtifactKind.THUMBNAIL, "ta", "short") is None
    assert caption_tracks(ARTIFACTS, "fr", "short") == ()
