from __future__ import annotations

from enum import StrEnum

from pydantic import AwareDatetime, Field

from autotube.domain.model_base import DomainModel


class Privacy(StrEnum):
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class ChannelStatus(StrEnum):
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ChannelDefaults(DomainModel):
    privacy: Privacy = Privacy.PRIVATE
    made_for_kids: bool = False
    category_id: str = Field(default="22", min_length=1)
    default_language: str = Field(default="en", min_length=1)
    notify_subscribers: bool = False


class Channel(DomainModel):
    id: str
    credential_id: str
    youtube_channel_id: str
    title: str
    thumbnail_url: str = ""
    status: ChannelStatus = ChannelStatus.CONNECTED
    defaults: ChannelDefaults = Field(default_factory=ChannelDefaults)
    connected_at: AwareDatetime


class ConnectStart(DomainModel):
    authorization_url: str
    state: str


def channel_token_secret_name(channel_id: str) -> str:
    return f"channel/{channel_id}/token"
