from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from automator.domain.channels import Channel, ChannelStatus
from automator.domain.ports import ChannelRepository
from automator.domain.youtube import AUTHORIZATION_EXPIRED_CODE
from automator.shared.errors import AppError


def is_expired_authorization(error: Exception) -> bool:
    return isinstance(error, AppError) and error.code == AUTHORIZATION_EXPIRED_CODE


@dataclass(frozen=True)
class ChannelExpiry:
    channels: ChannelRepository

    def mark_expired(self, channel: Channel) -> None:
        stored = self.channels.get(channel.id)
        if stored is not None and stored.status is not ChannelStatus.EXPIRED:
            self.channels.save(stored.model_copy(update={"status": ChannelStatus.EXPIRED}))

    @contextmanager
    def watching(self, channel: Channel) -> Iterator[None]:
        try:
            yield
        except Exception as error:
            if is_expired_authorization(error):
                self.mark_expired(channel)
            raise
