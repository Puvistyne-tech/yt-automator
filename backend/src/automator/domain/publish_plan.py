from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta

from pydantic import AwareDatetime

from automator.domain.artifact_selection import (
    VideoMetadata,
    best_artifact,
    caption_tracks,
    exact_video,
    video_metadata,
)
from automator.domain.automations import Target
from automator.domain.channels import Channel, ChannelDefaults, Privacy
from automator.domain.kids_rules import effective_made_for_kids, effective_privacy
from automator.domain.model_base import DomainModel
from automator.domain.pipeline_descriptors import PipelineDescriptor
from automator.domain.quota import QuotaPolicy, upload_cost
from automator.domain.run_enums import ArtifactKind, UploadStatus
from automator.domain.run_parts import Artifact, Upload
from automator.domain.runs import Run


class UploadPlan(DomainModel):
    target: Target
    channel: Channel | None
    language: str
    variant: str
    video: Artifact | None
    thumbnail: Artifact | None
    captions: tuple[Artifact, ...]
    metadata: VideoMetadata
    privacy: Privacy
    made_for_kids: bool
    publish_at: AwareDatetime | None

    @property
    def skip_reason(self) -> str | None:
        if self.channel is None:
            return f"channel {self.target.channel_id} no longer exists"
        if self.video is None:
            return f"no video for language {self.language} and variant {self.variant}"
        return None

    def cost(self, policy: QuotaPolicy) -> int:
        if self.skip_reason is not None:
            return 0
        return upload_cost(
            policy,
            thumbnail=self.thumbnail is not None,
            caption_tracks=len(self.captions),
            playlist=self.target.playlist_id is not None,
        )

    def initial_upload(self) -> Upload:
        skipped = self.skip_reason is not None
        return Upload(
            target_id=self.target.id,
            channel_id=self.target.channel_id,
            language=self.language,
            variant=self.variant,
            status=UploadStatus.SKIPPED if skipped else UploadStatus.PENDING,
            error=self.skip_reason,
        )


def scheduled_publish(target: Target, privacy: Privacy, now: datetime) -> datetime | None:
    if privacy is not Privacy.PUBLIC or target.publish_delay_minutes <= 0:
        return None
    return now + timedelta(minutes=target.publish_delay_minutes)


def plan_target_variant(
    run: Run,
    target: Target,
    variant: str,
    channel: Channel | None,
    descriptor: PipelineDescriptor | None,
    now: datetime,
) -> UploadPlan:
    defaults = channel.defaults if channel is not None else ChannelDefaults()
    privacy = effective_privacy(target, defaults)
    kids = effective_made_for_kids(target, defaults, descriptor)
    language = target.language
    return UploadPlan(
        target=target,
        channel=channel,
        language=language,
        variant=variant,
        video=exact_video(run.artifacts, language, variant),
        thumbnail=best_artifact(run.artifacts, ArtifactKind.THUMBNAIL, language, variant),
        captions=caption_tracks(run.artifacts, language, variant),
        metadata=video_metadata(run.artifacts, language, variant, run.automation_name),
        privacy=privacy,
        made_for_kids=kids,
        publish_at=scheduled_publish(target, privacy, now),
    )


def plan_uploads(
    run: Run,
    targets: Sequence[Target],
    channels: Mapping[str, Channel],
    descriptor: PipelineDescriptor | None,
    now: datetime,
) -> list[UploadPlan]:
    return [
        plan_target_variant(run, target, variant, channels.get(target.channel_id), descriptor, now)
        for target in targets
        if target.language in run.languages
        for variant in target.variants
    ]


def quota_needed(plans: Sequence[UploadPlan], policy: QuotaPolicy) -> dict[str, int]:
    needed: dict[str, int] = {}
    for plan in plans:
        if plan.channel is not None and plan.skip_reason is None:
            credential_id = plan.channel.credential_id
            needed[credential_id] = needed.get(credential_id, 0) + plan.cost(policy)
    return needed
