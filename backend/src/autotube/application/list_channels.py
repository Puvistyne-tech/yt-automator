from __future__ import annotations

from dataclasses import dataclass

from autotube.domain.channels import Channel
from autotube.domain.ports import ChannelRepository


@dataclass(frozen=True)
class ListChannels:
    channels: ChannelRepository

    def execute(self) -> list[Channel]:
        return sorted(self.channels.list(), key=lambda channel: channel.title.casefold())
