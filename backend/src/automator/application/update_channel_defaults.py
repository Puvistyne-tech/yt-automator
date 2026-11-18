from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require_channel
from automator.domain.channels import Channel, ChannelDefaults
from automator.domain.ports import ChannelRepository


@dataclass(frozen=True)
class UpdateChannelDefaults:
    channels: ChannelRepository

    def execute(self, channel_id: str, defaults: ChannelDefaults) -> Channel:
        channel = require_channel(self.channels, channel_id)
        updated = channel.model_copy(update={"defaults": defaults})
        self.channels.save(updated)
        return updated
