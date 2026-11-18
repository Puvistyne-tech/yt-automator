from __future__ import annotations

from dataclasses import dataclass

from automator.domain.channels import Channel
from automator.domain.ports import ChannelRepository


@dataclass(frozen=True)
class ListChannels:
    channels: ChannelRepository

    def execute(self) -> list[Channel]:
        return sorted(self.channels.list(), key=lambda channel: channel.title.casefold())
