from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial

from automator.application.channel_auth import ChannelAuthorizer
from automator.domain.channels import Channel
from automator.domain.ports import ArtifactStore, Clock, QuotaLedger, YouTubeGateway
from automator.domain.publish_plan import UploadPlan
from automator.domain.quota import QuotaPolicy
from automator.domain.run_enums import UploadStatus
from automator.domain.run_parts import Artifact, Upload
from automator.domain.youtube import ChannelAuth, VideoUpload


def describe(error: Exception) -> str:
    return str(error) or type(error).__name__


def failed_upload(base: Upload, error: Exception, units: int) -> Upload:
    return base.model_copy(
        update={"status": UploadStatus.FAILED, "error": describe(error), "quota_units": units}
    )


@dataclass
class UploadAttempt:
    run_id: str
    plan: UploadPlan
    channel: Channel
    auth: ChannelAuth
    units: int = 0
    problems: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UploadPerformer:
    youtube: YouTubeGateway
    store: ArtifactStore
    ledger: QuotaLedger
    authorizer: ChannelAuthorizer
    clock: Clock
    quota: QuotaPolicy = field(default_factory=QuotaPolicy)

    def perform(self, run_id: str, plan: UploadPlan) -> Upload:
        base = plan.initial_upload()
        if plan.channel is None or plan.video is None:
            return base
        try:
            auth = self.authorizer.auth(plan.channel)
        except Exception as error:
            return failed_upload(base, error, 0)
        attempt = UploadAttempt(run_id, plan, plan.channel, auth)
        self.charge(attempt, self.quota.video_units)
        try:
            uploaded = self.youtube.upload_video(auth, self.request(attempt, plan.video))
        except Exception as error:
            return failed_upload(base, error, attempt.units)
        self.finish_extras(attempt, uploaded.video_id)
        return base.model_copy(
            update={
                "status": UploadStatus.DONE,
                "youtube_video_id": uploaded.video_id,
                "url": uploaded.url,
                "error": "; ".join(attempt.problems) or None,
                "quota_units": attempt.units,
            }
        )

    def request(self, attempt: UploadAttempt, video: Artifact) -> VideoUpload:
        plan, defaults = attempt.plan, attempt.channel.defaults
        return VideoUpload(
            path=self.store.open(attempt.run_id, video),
            title=plan.metadata.title,
            description=plan.metadata.description,
            tags=plan.metadata.tags,
            category_id=defaults.category_id,
            default_language=plan.language,
            privacy=plan.privacy,
            made_for_kids=plan.made_for_kids,
            notify_subscribers=defaults.notify_subscribers,
            publish_at=plan.publish_at,
        )

    def charge(self, attempt: UploadAttempt, units: int) -> None:
        day = self.quota.quota_day(self.clock.now())
        self.ledger.record(attempt.channel.credential_id, units, day)
        attempt.units += units

    def extra(
        self, attempt: UploadAttempt, label: str, units: int, action: Callable[[], None]
    ) -> None:
        self.charge(attempt, units)
        try:
            action()
        except Exception as error:
            attempt.problems.append(f"{label}: {describe(error)}")

    def finish_extras(self, attempt: UploadAttempt, video_id: str) -> None:
        plan, auth, youtube, quota = attempt.plan, attempt.auth, self.youtube, self.quota
        if plan.thumbnail is not None:
            image = self.store.open(attempt.run_id, plan.thumbnail)
            action = partial(youtube.set_thumbnail, auth, video_id, image)
            self.extra(attempt, "thumbnail", quota.thumbnail_units, action)
        for track in plan.captions:
            language = track.language or plan.language
            path = self.store.open(attempt.run_id, track)
            action = partial(youtube.upload_captions, auth, video_id, language, path)
            self.extra(attempt, f"captions {language}", quota.caption_units, action)
        if plan.target.playlist_id is not None:
            action = partial(youtube.add_to_playlist, auth, video_id, plan.target.playlist_id)
            self.extra(attempt, "playlist", quota.playlist_item_units, action)
