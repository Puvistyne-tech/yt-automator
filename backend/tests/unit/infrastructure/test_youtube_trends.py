from __future__ import annotations

import json
from typing import Any

import httplib2  # type: ignore[import-untyped]
import pytest
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from autotube.domain.trends import TrendingVideo, TrendQuery
from autotube.infrastructure.youtube.gateway import GoogleYouTubeGateway
from autotube.infrastructure.youtube.sample_trends import SampleTrendSource
from autotube.infrastructure.youtube.trend_responses import duration_seconds, trending_video
from autotube.shared.errors import UpstreamFailure
from tests.unit.infrastructure.youtube_fakes import FakeService, auth

QUERY = TrendQuery(region="GB", category="27", limit=5)


def item(**snippet: Any) -> dict[str, Any]:
    return {
        "snippet": {"title": "Folding paper boats", "channelTitle": "Paper Corner"} | snippet,
        "contentDetails": {"duration": "PT4M13S"},
        "statistics": {"viewCount": "1200"},
        "status": {"madeForKids": False},
    }


def test_popular_videos_asks_for_the_most_popular_chart(
    gateway: GoogleYouTubeGateway, service: FakeService
) -> None:
    service.respond("videos", "list", {"items": [item(tags=["paper", "craft"], categoryId="27")]})
    [video] = gateway.popular_videos(auth(), QUERY)
    [(resource, method, kwargs)] = service.calls
    assert (resource, method) == ("videos", "list")
    assert kwargs == {
        "part": "snippet,contentDetails,statistics,status",
        "chart": "mostPopular",
        "regionCode": "GB",
        "maxResults": 5,
        "videoCategoryId": "27",
    }
    assert video == TrendingVideo(
        title="Folding paper boats",
        channel_title="Paper Corner",
        category_id="27",
        tags=("paper", "craft"),
        view_count=1200,
        duration_seconds=253,
        made_for_kids=False,
    )


def test_popular_videos_without_a_category_leaves_it_out(
    gateway: GoogleYouTubeGateway, service: FakeService
) -> None:
    gateway.popular_videos(auth(), TrendQuery(region="US", limit=3))
    [(_, _, kwargs)] = service.calls
    assert "videoCategoryId" not in kwargs


def test_popular_videos_turns_a_quota_error_into_an_upstream_failure(
    gateway: GoogleYouTubeGateway, service: FakeService
) -> None:
    body = {"error": {"errors": [{"reason": "quotaExceeded"}]}}
    failure = HttpError(httplib2.Response({"status": 403}), json.dumps(body).encode())
    service.respond("videos", "list", failure)
    with pytest.raises(UpstreamFailure) as raised:
        gateway.popular_videos(auth(), QUERY)
    assert raised.value.code == "youtube_quota_exceeded"


def test_untitled_and_malformed_items_are_skipped(
    gateway: GoogleYouTubeGateway, service: FakeService
) -> None:
    service.respond("videos", "list", {"items": [item(title=" "), "odd", item()]})
    assert [video.title for video in gateway.popular_videos(auth(), QUERY)] == [
        "Folding paper boats"
    ]


@pytest.mark.parametrize(
    "response",
    ["garbage", None, {"items": "many"}, {"items": [{"snippet": "odd"}]}],
)
def test_a_malformed_reply_gives_no_videos(
    gateway: GoogleYouTubeGateway, service: FakeService, response: object
) -> None:
    service.respond("videos", "list", response)
    assert gateway.popular_videos(auth(), QUERY) == []


def test_malformed_parts_of_an_item_take_safe_defaults() -> None:
    odd = {
        "snippet": {"title": "Quiet rain", "tags": "rain"},
        "statistics": [],
        "contentDetails": "PT1M",
        "status": {"madeForKids": "true"},
    }
    assert trending_video(odd) == TrendingVideo(title="Quiet rain")


def test_a_sparse_item_takes_safe_defaults() -> None:
    video = trending_video({"snippet": {"title": "Quiet rain"}, "statistics": {"viewCount": "x"}})
    assert video == TrendingVideo(title="Quiet rain")


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("PT4M13S", 253),
        ("PT1H", 3600),
        ("PT1H2M3S", 3723),
        ("P1W", 0),
        ("PT1.5S", 0),
        ("P1DT2S", 86402),
        ("PT45S", 45),
        ("soon", 0),
        ("", 0),
    ],
)
def test_iso_durations_become_seconds(text: str, seconds: int) -> None:
    assert duration_seconds(text) == seconds


def test_the_sample_source_returns_bundled_neutral_videos_up_to_the_limit() -> None:
    videos = SampleTrendSource().trending(TrendQuery(region="US", limit=4))
    assert len(videos) == 4
    assert all(video.title and video.channel_title for video in videos)


def test_the_sample_source_prefers_the_requested_category() -> None:
    videos = SampleTrendSource().trending(TrendQuery(region="US", category="27", limit=50))
    assert videos
    assert {video.category_id for video in videos} == {"27"}


def test_the_sample_source_flags_some_videos_made_for_kids() -> None:
    videos = SampleTrendSource().trending(TrendQuery(region="US", limit=50))
    assert {video.made_for_kids for video in videos} >= {True, False}
