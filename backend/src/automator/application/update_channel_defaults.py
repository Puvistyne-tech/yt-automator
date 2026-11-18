from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require
from automator.domain.channels import Channel, ChannelDefaults
from automator.domain.ports import ChannelRepository


@dataclass(frozen=True)
class UpdateChannelDefaults:
    channels: ChannelRepository

    def execute(self, channel_id: str, defaults: ChannelDefaults) -> Channel:
        channel = require(self.channels.get(channel_id), "channel", channel_id)
        updated = channel.model_copy(update={"defaults": defaults})
        self.channels.save(updated)
        return updated
