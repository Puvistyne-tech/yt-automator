from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from autotube.domain.channels import Privacy
from autotube.domain.youtube import Playlist, VideoUpload
from autotube.infrastructure.youtube.gateway import GoogleYouTubeGateway
from autotube.shared.errors import UpstreamFailure
from tests.unit.infrastructure.youtube_fakes import EXPIRED_TOKEN, FakeService, auth


def video(path: Path, publish_at: datetime | None = None) -> VideoUpload:
    return VideoUpload(
        path=path,
        title="Owls",
        description="A story",
        tags=("kids", "owls"),
        category_id="27",
        default_language="ta",
        privacy=Privacy.PUBLIC,
        made_for_kids=True,
        notify_subscribers=False,
        publish_at=publish_at,
    )


def test_upload_builds_a_resumable_insert(
    gateway: GoogleYouTubeGateway, service: FakeService, tmp_path: Path
) -> None:
    service.chunks = 3
    service.respond("videos", "insert", {"id": "vid-9"})
    at = datetime(2026, 2, 1, 9, 30, tzinfo=UTC)
    uploaded = gateway.upload_video(auth(), video(tmp_path / "v.mp4", at))
    assert (uploaded.video_id, uploaded.url) == ("vid-9", "https://youtu.be/vid-9")
    [(resource, method, kwargs)] = service.calls
    assert (resource, method, kwargs["part"]) == ("videos", "insert", "snippet,status")
    assert kwargs["notifySubscribers"] is False
    assert kwargs["media_body"] == {
        "path": str(tmp_path / "v.mp4"),
        "chunksize": 256 * 1024,
        "resumable": True,
    }
    body = kwargs["body"]
    assert (body["snippet"]["title"], body["snippet"]["description"]) == ("Owls", "A story")
    assert body["snippet"]["defaultAudioLanguage"] == "ta"
    assert body["snippet"]["tags"] == ["kids", "owls"]
    assert (body["snippet"]["categoryId"], body["snippet"]["defaultLanguage"]) == ("27", "ta")
    assert body["status"] == {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": True,
        "publishAt": "2026-02-01T09:30:00Z",
    }


def test_upload_without_schedule_keeps_privacy(
    gateway: GoogleYouTubeGateway, service: FakeService, tmp_path: Path
) -> None:
    service.respond("videos", "insert", {"id": "v"})
    gateway.upload_video(auth(), video(tmp_path / "v.mp4"))
    assert service.calls[0][2]["body"]["status"]["privacyStatus"] == "public"


def test_upload_without_id_is_an_upstream_failure(
    gateway: GoogleYouTubeGateway, tmp_path: Path
) -> None:
    with pytest.raises(UpstreamFailure, match="video id"):
        gateway.upload_video(auth(), video(tmp_path / "v.mp4"))


def test_thumbnail_captions_and_playlist_requests(
    gateway: GoogleYouTubeGateway, service: FakeService, tmp_path: Path
) -> None:
    gateway.set_thumbnail(auth(), "v1", tmp_path / "t.png")
    gateway.upload_captions(auth(), "v1", "ta", tmp_path / "ta.srt")
    gateway.add_to_playlist(auth(), "v1", "PL1")
    thumbnail, captions, playlist = service.calls
    assert thumbnail[:2] == ("thumbnails", "set")
    assert thumbnail[2] == {"videoId": "v1", "media_body": {"path": str(tmp_path / "t.png")}}
    assert captions[:2] == ("captions", "insert")
    assert captions[2]["body"]["snippet"] == {
        "videoId": "v1",
        "language": "ta",
        "name": "",
        "isDraft": False,
    }
    assert captions[2]["media_body"]["mimetype"] == "application/octet-stream"
    assert playlist[2]["body"]["snippet"] == {
        "playlistId": "PL1",
        "resourceId": {"kind": "youtube#video", "videoId": "v1"},
    }


def test_list_playlists_follows_pages(gateway: GoogleYouTubeGateway, service: FakeService) -> None:
    service.respond(
        "playlists",
        "list",
        {"items": [{"id": "a", "snippet": {"title": "A"}}], "nextPageToken": "p2"},
        {"items": [{"id": "b", "snippet": {"title": "B"}}]},
    )
    assert gateway.list_playlists(auth()) == [
        Playlist(id="a", title="A"),
        Playlist(id="b", title="B"),
    ]
    tokens = [kwargs["pageToken"] for _, _, kwargs in service.calls]
    assert tokens == [None, "p2"]
    assert service.calls[0][2]["maxResults"] == 2


def test_describe_channel_reads_the_snippet(
    gateway: GoogleYouTubeGateway, service: FakeService
) -> None:
    item = {"id": "UC1", "snippet": {"title": "Kids", "thumbnails": {"default": {"url": "u"}}}}
    service.respond("channels", "list", {"items": [item]})
    profile = gateway.describe_channel(auth())
    assert (profile.youtube_channel_id, profile.title, profile.thumbnail_url) == (
        "UC1",
        "Kids",
        "u",
    )
    service.respond("channels", "list", {"items": []})
    with pytest.raises(UpstreamFailure) as raised:
        gateway.describe_channel(auth())
    assert raised.value.code == "youtube_no_channel"


def test_expired_tokens_are_refreshed_and_bad_tokens_rejected(
    gateway: GoogleYouTubeGateway, refreshed: list[str]
) -> None:
    gateway.add_to_playlist(auth(), "v", "p")
    assert refreshed == []
    gateway.add_to_playlist(auth(EXPIRED_TOKEN), "v", "p")
    assert refreshed == ["rt"]
    with pytest.raises(UpstreamFailure) as raised:
        gateway.add_to_playlist(auth().model_copy(update={"token": "not json"}), "v", "p")
    assert raised.value.code == "youtube_token_invalid"
