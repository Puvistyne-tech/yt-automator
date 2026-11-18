from __future__ import annotations

from dataclasses import dataclass

from automator.application.channel_auth import ChannelAuthorizer
from automator.application.lookups import require
from automator.domain.ports import ChannelRepository, YouTubeGateway
from automator.domain.youtube import Playlist


@dataclass(frozen=True)
class ListChannelPlaylists:
    channels: ChannelRepository
    authorizer: ChannelAuthorizer
    youtube: YouTubeGateway

    def execute(self, channel_id: str) -> list[Playlist]:
        channel = require(self.channels.get(channel_id), "channel", channel_id)
        return self.youtube.list_playlists(self.authorizer.auth(channel))
