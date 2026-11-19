from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum

from pydantic import Field

from autotube.domain.channels import Channel, ChannelStatus
from autotube.domain.model_base import DomainModel
from autotube.domain.pipeline_templates import TemplateAudience

REGION_PATTERN = r"^[A-Z]{2}$"
CATEGORY_PATTERN = r"^[0-9]{1,4}$"


class TrendOrigin(StrEnum):
    YOUTUBE = "youtube"
    SAMPLE = "sample"


class TrendingVideo(DomainModel):
    title: str
    channel_title: str = ""
    category_id: str = ""
    tags: tuple[str, ...] = ()
    view_count: int = Field(default=0, ge=0)
    duration_seconds: int = Field(default=0, ge=0)
    made_for_kids: bool | None = None


class TrendQuery(DomainModel):
    region: str = Field(pattern=REGION_PATTERN)
    category: str | None = Field(default=None, pattern=CATEGORY_PATTERN)
    limit: int = Field(ge=1)


class TrendReport(DomainModel):
    origin: TrendOrigin
    videos: tuple[TrendingVideo, ...]


def first_connected(channels: Iterable[Channel]) -> Channel | None:
    return next((c for c in channels if c.status is ChannelStatus.CONNECTED), None)


def sample_selection(
    videos: Sequence[TrendingVideo], query: TrendQuery
) -> tuple[TrendingVideo, ...]:
    matching = [video for video in videos if video.category_id == query.category]
    return tuple((matching or videos)[: query.limit])


def audience_trends(
    videos: Sequence[TrendingVideo], audience: TemplateAudience
) -> tuple[TrendingVideo, ...]:
    if audience is TemplateAudience.KIDS:
        return tuple(videos)
    return tuple(video for video in videos if video.made_for_kids is not True)
