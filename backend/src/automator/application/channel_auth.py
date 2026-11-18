from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import require_credential
from automator.domain.channels import Channel, channel_token_secret_name
from automator.domain.credentials import Credential, credential_secret_name
from automator.domain.ports import CredentialRepository, SecretStore
from automator.domain.youtube import ChannelAuth, OAuthClient
from automator.shared.errors import RuleConflict


@dataclass(frozen=True)
class ChannelAuthorizer:
    credentials: CredentialRepository
    secrets: SecretStore

    def client_secret(self, credential: Credential) -> str:
        secret = self.secrets.get(credential_secret_name(credential.id))
        if not secret:
            raise RuleConflict(
                "credential_secret_missing", f"credential {credential.id} has no client secret"
            )
        return secret

    def client(self, credential: Credential) -> OAuthClient:
        return OAuthClient(
            client_id=credential.client_id, client_secret=self.client_secret(credential)
        )

    def credential_of(self, channel: Channel) -> Credential:
        return require_credential(self.credentials, channel.credential_id)

    def auth(self, channel: Channel) -> ChannelAuth:
        token = self.secrets.get(channel_token_secret_name(channel.id))
        if not token:
            raise RuleConflict(
                "channel_not_authorized", f"channel {channel.id} has no stored authorization"
            )
        return ChannelAuth(client=self.client(self.credential_of(channel)), token=token)
