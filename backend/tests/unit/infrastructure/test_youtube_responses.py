from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from autotube.domain.youtube import Playlist
from autotube.infrastructure.youtube.gateway import GoogleYouTubeGateway
from autotube.infrastructure.youtube.settings import YouTubeSettings
from tests.unit.infrastructure.youtube_fakes import FakeService, auth, media

H, M, D = {"url": "h"}, {"url": "m"}, {"url": "d"}


@pytest.mark.parametrize(
    ("item", "title", "thumbnail"),
    [
        (
            {"snippet": {"title": "K", "thumbnails": {"high": H, "medium": M, "default": D}}},
            "K",
            "h",
        ),
        ({"snippet": {"title": "K", "thumbnails": {"medium": M, "default": D}}}, "K", "m"),
        ({"snippet": {"title": "K", "thumbnails": {}}}, "K", ""),
        ({}, "", ""),
    ],
)
def test_describe_channel_picks_the_largest_thumbnail(
    gateway: GoogleYouTubeGateway,
    service: FakeService,
    item: dict[str, Any],
    title: str,
    thumbnail: str,
) -> None:
    service.respond("channels", "list", {"items": [{"id": "UC1"} | item]})
    profile = gateway.describe_channel(auth())
    assert (profile.title, profile.thumbnail_url) == (title, thumbnail)


def test_playlists_without_a_snippet_have_an_empty_title(
    gateway: GoogleYouTubeGateway, service: FakeService
) -> None:
    service.respond("playlists", "list", {"items": [{"id": "a"}]})
    assert gateway.list_playlists(auth()) == [Playlist(id="a", title="")]


def test_captions_use_the_configured_track_name(service: FakeService, tmp_path: Path) -> None:
    settings = YouTubeSettings(caption_track_name="English")
    gateway = GoogleYouTubeGateway(settings, services=lambda _c: service, media=media)
    gateway.upload_captions(auth(), "v1", "en", tmp_path / "en.srt")
    assert service.calls[0][2]["body"]["snippet"]["name"] == "English"
