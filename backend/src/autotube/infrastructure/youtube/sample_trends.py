from __future__ import annotations

from functools import cache
from importlib.resources import files

from pydantic import TypeAdapter

from autotube.domain.trends import TrendingVideo, TrendQuery, sample_selection

SAMPLE_FILE = "sample_trends.json"
SAMPLE_VIDEOS = TypeAdapter(tuple[TrendingVideo, ...])


@cache
def bundled_videos() -> tuple[TrendingVideo, ...]:
    text = files(__package__ or "").joinpath(SAMPLE_FILE).read_text(encoding="utf-8")
    return SAMPLE_VIDEOS.validate_json(text)


class SampleTrendSource:
    def trending(self, query: TrendQuery) -> list[TrendingVideo]:
        return list(sample_selection(bundled_videos(), query))
