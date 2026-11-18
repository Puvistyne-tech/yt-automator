from __future__ import annotations

from dataclasses import dataclass

from autotube.application.lookups import require_channel
from autotube.domain.channels import Channel, ChannelDefaults
from autotube.domain.ports import ChannelRepository


@dataclass(frozen=True)
class UpdateChannelDefaults:
    channels: ChannelRepository

    def execute(self, channel_id: str, defaults: ChannelDefaults) -> Channel:
        channel = require_channel(self.channels, channel_id)
        updated = channel.model_copy(update={"defaults": defaults})
        self.channels.save(updated)
        return updated
