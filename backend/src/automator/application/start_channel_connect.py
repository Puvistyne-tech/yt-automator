from __future__ import annotations

from dataclasses import dataclass

from automator.application.channel_auth import ChannelAuthorizer
from automator.application.lookups import require_credential
from automator.domain.channels import ConnectStart
from automator.domain.connect_state import ConnectState, issue_state
from automator.domain.ports import Clock, CredentialRepository, IdGenerator, YouTubeGateway


@dataclass(frozen=True)
class StartChannelConnect:
    credentials: CredentialRepository
    authorizer: ChannelAuthorizer
    youtube: YouTubeGateway
    ids: IdGenerator
    clock: Clock

    def execute(self, credential_id: str) -> ConnectStart:
        credential = require_credential(self.credentials, credential_id)
        client = self.authorizer.client(credential)
        state = ConnectState(
            credential_id=credential.id, nonce=self.ids.new(), issued_at=self.clock.now()
        )
        token = issue_state(state, client.client_secret)
        return ConnectStart(
            authorization_url=self.youtube.authorization_url(client, token), state=token
        )
