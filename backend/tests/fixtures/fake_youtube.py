from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from automator.domain.youtube import (
    ChannelAuth,
    ChannelProfile,
    OAuthClient,
    Playlist,
    UploadedVideo,
    VideoUpload,
)
from automator.shared.errors import UpstreamFailure


@dataclass
class FakeYouTube:
    profile: ChannelProfile = field(
        default_factory=lambda: ChannelProfile(
            youtube_channel_id="UC-fake", title="Fake Channel", thumbnail_url="https://img/fake"
        )
    )
    playlists: list[Playlist] = field(
        default_factory=lambda: [Playlist(id="PL-1", title="Stories")]
    )
    failing_videos: set[str] = field(default_factory=set)
    failing_operations: set[str] = field(default_factory=set)
    failure_code: str = "upstream_failure"
    uploads: list[VideoUpload] = field(default_factory=list)
    calls: list[tuple[str, str]] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)

    def record(self, auth: ChannelAuth, operation: str, detail: str) -> None:
        self.tokens.append(auth.token)
        self.calls.append((operation, detail))

    def check(self, operation: str) -> None:
        if operation in self.failing_operations:
            raise UpstreamFailure(f"{operation} rejected", self.failure_code)

    def authorization_url(self, client: OAuthClient, state: str) -> str:
        return f"https://accounts.example/auth?client_id={client.client_id}&state={state}"

    def exchange_code(self, client: OAuthClient, code: str) -> str:
        self.check("exchange_code")
        return f"token-for-{code}-{client.client_id}"

    def describe_channel(self, auth: ChannelAuth) -> ChannelProfile:
        self.check("describe_channel")
        self.record(auth, "describe_channel", auth.token)
        return self.profile

    def upload_video(self, auth: ChannelAuth, video: VideoUpload) -> UploadedVideo:
        self.record(auth, "upload_video", video.path.name)
        if video.path.name in self.failing_videos:
            raise UpstreamFailure(f"upload of {video.path.name} rejected", self.failure_code)
        self.uploads.append(video)
        video_id = f"vid-{len(self.uploads)}"
        return UploadedVideo(video_id=video_id, url=f"https://youtu.be/{video_id}")

    def set_thumbnail(self, auth: ChannelAuth, video_id: str, image: Path) -> None:
        self.record(auth, "set_thumbnail", f"{video_id}:{image.name}")
        self.check("set_thumbnail")

    def upload_captions(
        self, auth: ChannelAuth, video_id: str, language: str, captions: Path
    ) -> None:
        self.record(auth, "upload_captions", f"{video_id}:{language}:{captions.name}")
        self.check("upload_captions")

    def add_to_playlist(self, auth: ChannelAuth, video_id: str, playlist_id: str) -> None:
        self.record(auth, "add_to_playlist", f"{video_id}:{playlist_id}")
        self.check("add_to_playlist")

    def list_playlists(self, auth: ChannelAuth) -> list[Playlist]:
        self.record(auth, "list_playlists", "")
        self.check("list_playlists")
        return list(self.playlists)

    def operations(self, name: str) -> list[str]:
        return [detail for operation, detail in self.calls if operation == name]
