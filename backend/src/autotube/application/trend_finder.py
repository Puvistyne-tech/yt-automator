from __future__ import annotations

from dataclasses import dataclass

from autotube.application.channel_auth import ChannelAuthorizer
from autotube.application.channel_expiry import ChannelExpiry
from autotube.application.quota_report import QuotaReport
from autotube.domain.channels import Channel
from autotube.domain.credentials import Credential
from autotube.domain.ports import (
    ChannelRepository,
    CredentialRepository,
    TrendSource,
    YouTubeGateway,
)
from autotube.domain.trends import (
    TrendingVideo,
    TrendOrigin,
    TrendQuery,
    TrendReport,
    first_connected,
)
from autotube.shared.errors import AppError


@dataclass(frozen=True)
class TrendFinder:
    channels: ChannelRepository
    credentials: CredentialRepository
    authorizer: ChannelAuthorizer
    youtube: YouTubeGateway
    quota_report: QuotaReport
    expiry: ChannelExpiry
    sample: TrendSource

    def find(self, query: TrendQuery) -> TrendReport:
        try:
            videos = self.from_youtube(query)
        except AppError:
            videos = []
        if videos:
            return TrendReport(origin=TrendOrigin.YOUTUBE, videos=tuple(videos))
        return TrendReport(origin=TrendOrigin.SAMPLE, videos=tuple(self.sample.trending(query)))

    def from_youtube(self, query: TrendQuery) -> list[TrendingVideo]:
        channel = first_connected(self.channels.list())
        credential = None if channel is None else self.credentials.get(channel.credential_id)
        if channel is None or credential is None or not self.affordable(credential):
            return []
        return self.charged_call(channel, credential, query)

    def affordable(self, credential: Credential) -> bool:
        units = self.quota_report.policy.trending_units
        return self.quota_report.usage(credential).remaining >= units

    def charged_call(
        self, channel: Channel, credential: Credential, query: TrendQuery
    ) -> list[TrendingVideo]:
        auth = self.authorizer.auth(channel)
        self.quota_report.charge(credential.id, self.quota_report.policy.trending_units)
        with self.expiry.watching(channel):
            return self.youtube.popular_videos(auth, query)
