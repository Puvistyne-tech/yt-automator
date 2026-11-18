from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require
from automator.domain.channels import channel_token_secret_name
from automator.domain.deletion_rules import ensure_channel_deletable
from automator.domain.ports import AutomationRepository, ChannelRepository, SecretStore


@dataclass(frozen=True)
class DeleteChannel:
    channels: ChannelRepository
    automations: AutomationRepository
    secrets: SecretStore

    def execute(self, channel_id: str) -> None:
        require(self.channels.get(channel_id), "channel", channel_id)
        ensure_channel_deletable(channel_id, self.automations.list())
        self.secrets.delete(channel_token_secret_name(channel_id))
        self.channels.delete(channel_id)
