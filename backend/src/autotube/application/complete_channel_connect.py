from __future__ import annotations

from dataclasses import dataclass, field

from autotube.application.channel_auth import ChannelAuthorizer
from autotube.domain.channels import (
    Channel,
    ChannelDefaults,
    ChannelStatus,
    channel_token_secret_name,
)
from autotube.domain.connect_state import (
    ConnectStatePolicy,
    invalid_state,
    read_state,
    verify_state,
)
from autotube.domain.credentials import Credential
from autotube.domain.ports import (
    ChannelRepository,
    Clock,
    CredentialRepository,
    IdGenerator,
    SecretStore,
    YouTubeGateway,
)
from autotube.domain.youtube import ChannelAuth, ChannelProfile


@dataclass(frozen=True)
class CompleteChannelConnect:
    credentials: CredentialRepository
    channels: ChannelRepository
    authorizer: ChannelAuthorizer
    secrets: SecretStore
    youtube: YouTubeGateway
    ids: IdGenerator
    clock: Clock
    policy: ConnectStatePolicy = field(default_factory=ConnectStatePolicy)

    def execute(self, code: str, state: str) -> Channel:
        credential = self.verified_credential(state)
        client = self.authorizer.client(credential)
        token = self.youtube.exchange_code(client, code)
        profile = self.youtube.describe_channel(ChannelAuth(client=client, token=token))
        channel = self.connected_channel(credential, profile)
        self.secrets.set(channel_token_secret_name(channel.id), token)
        self.channels.save(channel)
        return channel

    def verified_credential(self, token: str) -> Credential:
        state = read_state(token)
        credential = self.credentials.get(state.credential_id)
        if credential is None:
            raise invalid_state("unknown credential")
        key = self.authorizer.client_secret(credential)
        verify_state(token, state, key, self.clock.now(), self.policy)
        return credential

    def connected_channel(self, credential: Credential, profile: ChannelProfile) -> Channel:
        existing = self.channels.find_by_youtube_id(profile.youtube_channel_id)
        return Channel(
            id=existing.id if existing is not None else self.ids.new(),
            credential_id=credential.id,
            youtube_channel_id=profile.youtube_channel_id,
            title=profile.title,
            thumbnail_url=profile.thumbnail_url,
            status=ChannelStatus.CONNECTED,
            defaults=existing.defaults if existing is not None else ChannelDefaults(),
            connected_at=self.clock.now(),
        )
