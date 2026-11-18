from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require_credential
from automator.domain.credentials import credential_secret_name
from automator.domain.deletion_rules import ensure_credential_deletable
from automator.domain.ports import ChannelRepository, CredentialRepository, SecretStore


@dataclass(frozen=True)
class DeleteCredential:
    credentials: CredentialRepository
    channels: ChannelRepository
    secrets: SecretStore

    def execute(self, credential_id: str) -> None:
        require_credential(self.credentials, credential_id)
        ensure_credential_deletable(credential_id, self.channels.list())
        self.secrets.delete(credential_secret_name(credential_id))
        self.credentials.delete(credential_id)
