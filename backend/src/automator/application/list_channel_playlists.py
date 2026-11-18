from __future__ import annotations

from dataclasses import dataclass

from automator.application.channel_auth import ChannelAuthorizer
from automator.application.channel_expiry import ChannelExpiry
from automator.application.lookups import require_channel
from automator.domain.ports import ChannelRepository, YouTubeGateway
from automator.domain.youtube import Playlist


@dataclass(frozen=True)
class ListChannelPlaylists:
    channels: ChannelRepository
    authorizer: ChannelAuthorizer
    youtube: YouTubeGateway
    expiry: ChannelExpiry

    def execute(self, channel_id: str) -> list[Playlist]:
        channel = require_channel(self.channels, channel_id)
        auth = self.authorizer.auth(channel)
        with self.expiry.watching(channel):
            return self.youtube.list_playlists(auth)
