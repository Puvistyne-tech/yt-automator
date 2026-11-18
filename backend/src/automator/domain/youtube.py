from __future__ import annotations

from pathlib import Path

from pydantic import AwareDatetime, Field

from automator.domain.channels import Privacy
from automator.domain.model_base import DomainModel


class OAuthClient(DomainModel):
    client_id: str
    client_secret: str = Field(repr=False)


class ChannelAuth(DomainModel):
    client: OAuthClient
    token: str = Field(repr=False)


class ChannelProfile(DomainModel):
    youtube_channel_id: str
    title: str
    thumbnail_url: str = ""


class Playlist(DomainModel):
    id: str
    title: str


class VideoUpload(DomainModel):
    path: Path
    title: str
    description: str = ""
    tags: tuple[str, ...] = ()
    category_id: str
    default_language: str
    privacy: Privacy
    made_for_kids: bool
    notify_subscribers: bool
    publish_at: AwareDatetime | None = None


class UploadedVideo(DomainModel):
    video_id: str
    url: str


AUTHORIZATION_EXPIRED_CODE = "youtube_invalid_grant"
