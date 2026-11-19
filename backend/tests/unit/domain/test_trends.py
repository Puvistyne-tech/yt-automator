from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from autotube.domain.channels import Channel, ChannelStatus
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.trends import (
    TrendingVideo,
    TrendQuery,
    audience_trends,
    first_connected,
    sample_selection,
)

NOW = datetime(2026, 3, 1, tzinfo=UTC)
CRAFT = TrendingVideo(title="Paper boats", category_id="26")
LESSON = TrendingVideo(title="Counting ducks", category_id="27", made_for_kids=True)
UNKNOWN = TrendingVideo(title="Night sky", category_id="28")


def channel(channel_id: str, status: ChannelStatus) -> Channel:
    return Channel(
        id=channel_id,
        credential_id="cred",
        youtube_channel_id=f"UC-{channel_id}",
        title=channel_id,
        status=status,
        connected_at=NOW,
    )


def test_the_first_connected_channel_is_chosen() -> None:
    channels = [channel("a", ChannelStatus.EXPIRED), channel("b", ChannelStatus.CONNECTED)]
    chosen = first_connected(channels)
    assert chosen is not None
    assert chosen.id == "b"


def test_no_connected_channel_gives_none() -> None:
    assert first_connected([channel("a", ChannelStatus.REVOKED)]) is None


def test_general_audiences_never_see_made_for_kids_trends() -> None:
    assert audience_trends([CRAFT, LESSON, UNKNOWN], TemplateAudience.GENERAL) == (CRAFT, UNKNOWN)


def test_kids_audiences_keep_every_trend() -> None:
    assert audience_trends([CRAFT, LESSON], TemplateAudience.KIDS) == (CRAFT, LESSON)


def test_a_sample_selection_prefers_the_category_and_respects_the_limit() -> None:
    videos = [CRAFT, LESSON, UNKNOWN]
    assert sample_selection(videos, TrendQuery(region="US", category="27", limit=5)) == (LESSON,)
    assert sample_selection(videos, TrendQuery(region="US", category="99", limit=2)) == (
        CRAFT,
        LESSON,
    )
    assert sample_selection(videos, TrendQuery(region="US", limit=1)) == (CRAFT,)


@pytest.mark.parametrize(
    "fields",
    [{"region": "gb"}, {"region": "GBR"}, {"category": "music"}, {"limit": 0}],
)
def test_a_trend_query_refuses_bad_values(fields: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TrendQuery.model_validate({"region": "GB", "limit": 5} | fields)
