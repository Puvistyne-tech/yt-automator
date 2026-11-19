from __future__ import annotations

from pathlib import Path
from typing import Protocol

from autotube.domain.trends import TrendingVideo, TrendQuery
from autotube.domain.youtube import (
    ChannelAuth,
    ChannelProfile,
    OAuthClient,
    Playlist,
    UploadedVideo,
    VideoUpload,
)


class YouTubeGateway(Protocol):
    def authorization_url(self, client: OAuthClient, state: str) -> str: ...

    def exchange_code(self, client: OAuthClient, code: str) -> str: ...

    def describe_channel(self, auth: ChannelAuth) -> ChannelProfile: ...

    def upload_video(self, auth: ChannelAuth, video: VideoUpload) -> UploadedVideo: ...

    def set_thumbnail(self, auth: ChannelAuth, video_id: str, image: Path) -> None: ...

    def upload_captions(
        self, auth: ChannelAuth, video_id: str, language: str, captions: Path
    ) -> None: ...

    def add_to_playlist(self, auth: ChannelAuth, video_id: str, playlist_id: str) -> None: ...

    def list_playlists(self, auth: ChannelAuth) -> list[Playlist]: ...

    def popular_videos(self, auth: ChannelAuth, query: TrendQuery) -> list[TrendingVideo]: ...


class TrendSource(Protocol):
    def trending(self, query: TrendQuery) -> list[TrendingVideo]: ...
