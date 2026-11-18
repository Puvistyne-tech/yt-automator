from __future__ import annotations

from dataclasses import dataclass

from autotube.application.lookups import require_channel
from autotube.domain.channels import channel_token_secret_name
from autotube.domain.deletion_rules import ensure_channel_deletable
from autotube.domain.ports import AutomationRepository, ChannelRepository, SecretStore


@dataclass(frozen=True)
class DeleteChannel:
    channels: ChannelRepository
    automations: AutomationRepository
    secrets: SecretStore

    def execute(self, channel_id: str) -> None:
        require_channel(self.channels, channel_id)
        ensure_channel_deletable(channel_id, self.automations.list())
        self.secrets.delete(channel_token_secret_name(channel_id))
        self.channels.delete(channel_id)
