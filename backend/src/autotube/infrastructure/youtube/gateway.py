from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.http import MediaFileUpload  # type: ignore[import-untyped]

from autotube.domain.trends import TrendingVideo, TrendQuery
from autotube.domain.youtube import (
    ChannelAuth,
    ChannelProfile,
    OAuthClient,
    Playlist,
    UploadedVideo,
    VideoUpload,
)
from autotube.infrastructure.youtube.errors import google_errors
from autotube.infrastructure.youtube.oauth import (
    GoogleOAuth,
    Refresher,
    load_credentials,
    refresh_with_google,
)
from autotube.infrastructure.youtube.request_bodies import (
    caption_body,
    channel_profile,
    playlist_item_body,
    video_body,
)
from autotube.infrastructure.youtube.settings import YouTubeSettings
from autotube.infrastructure.youtube.trend_responses import trending_parameters, trending_videos
from autotube.shared.errors import UpstreamFailure

ServiceFactory = Callable[[Credentials], Any]
MediaFactory = Callable[..., Any]
CaptionName = Callable[[], str]
CAPTION_MEDIA_TYPE = "application/octet-stream"


def youtube_service(credentials: Credentials) -> Any:
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


class GoogleYouTubeGateway:
    def __init__(
        self,
        settings: YouTubeSettings,
        services: ServiceFactory = youtube_service,
        media: MediaFactory = MediaFileUpload,
        oauth: GoogleOAuth | None = None,
        refresher: Refresher = refresh_with_google,
        caption_name: CaptionName | None = None,
    ) -> None:
        self.settings = settings
        self.caption_name = caption_name or (lambda: settings.caption_track_name)
        self.services = services
        self.media = media
        self.oauth = oauth or GoogleOAuth(settings)
        self.refresher = refresher

    def service(self, auth: ChannelAuth) -> Any:
        return self.services(load_credentials(auth, self.refresher))

    def authorization_url(self, client: OAuthClient, state: str) -> str:
        return self.oauth.authorization_url(client, state)

    def exchange_code(self, client: OAuthClient, code: str) -> str:
        return self.oauth.exchange_code(client, code)

    def describe_channel(self, auth: ChannelAuth) -> ChannelProfile:
        with google_errors():
            response = self.service(auth).channels().list(part="snippet", mine=True).execute()
        return channel_profile(response)

    def upload_video(self, auth: ChannelAuth, video: VideoUpload) -> UploadedVideo:
        media = self.media(
            str(video.path), chunksize=self.settings.upload_chunk_bytes, resumable=True
        )
        with google_errors():
            request = (
                self.service(auth)
                .videos()
                .insert(
                    part="snippet,status",
                    body=video_body(video),
                    media_body=media,
                    notifySubscribers=video.notify_subscribers,
                )
            )
            response = self.finish_resumable(request)
        video_id = str(response.get("id", ""))
        if not video_id:
            raise UpstreamFailure("YouTube did not return a video id", "youtube_upload_incomplete")
        return UploadedVideo(video_id=video_id, url=self.settings.watch_url_prefix + video_id)

    def finish_resumable(self, request: Any) -> dict[str, Any]:
        response: dict[str, Any] | None = None
        while response is None:
            _, response = request.next_chunk()
        return response

    def set_thumbnail(self, auth: ChannelAuth, video_id: str, image: Path) -> None:
        with google_errors():
            self.service(auth).thumbnails().set(
                videoId=video_id, media_body=self.media(str(image))
            ).execute()

    def upload_captions(
        self, auth: ChannelAuth, video_id: str, language: str, captions: Path
    ) -> None:
        body = caption_body(video_id, language, self.caption_name())
        media = self.media(str(captions), mimetype=CAPTION_MEDIA_TYPE)
        with google_errors():
            self.service(auth).captions().insert(
                part="snippet", body=body, media_body=media
            ).execute()

    def add_to_playlist(self, auth: ChannelAuth, video_id: str, playlist_id: str) -> None:
        with google_errors():
            self.service(auth).playlistItems().insert(
                part="snippet", body=playlist_item_body(video_id, playlist_id)
            ).execute()

    def popular_videos(self, auth: ChannelAuth, query: TrendQuery) -> list[TrendingVideo]:
        with google_errors():
            response = self.service(auth).videos().list(**trending_parameters(query)).execute()
        return trending_videos(response)

    def list_playlists(self, auth: ChannelAuth) -> list[Playlist]:
        playlists: list[Playlist] = []
        page_token: str | None = None
        with google_errors():
            resource = self.service(auth).playlists()
            while True:
                response = resource.list(
                    part="snippet",
                    mine=True,
                    maxResults=self.settings.playlist_page_size,
                    pageToken=page_token,
                ).execute()
                playlists += [
                    Playlist(id=item["id"], title=item.get("snippet", {}).get("title", ""))
                    for item in response.get("items", [])
                ]
                page_token = response.get("nextPageToken")
                if not page_token:
                    return playlists
