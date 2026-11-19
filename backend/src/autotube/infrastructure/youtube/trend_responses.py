from __future__ import annotations

import re
from typing import Any

from autotube.domain.trends import TrendingVideo, TrendQuery

TRENDING_PARTS = "snippet,contentDetails,statistics,status"
MOST_POPULAR = "mostPopular"
DURATION = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)
UNIT_SECONDS = {"days": 86400, "hours": 3600, "minutes": 60, "seconds": 1}


def trending_parameters(query: TrendQuery) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "part": TRENDING_PARTS,
        "chart": MOST_POPULAR,
        "regionCode": query.region,
        "maxResults": query.limit,
    }
    if query.category is not None:
        parameters["videoCategoryId"] = query.category
    return parameters


def duration_seconds(text: str) -> int:
    found = DURATION.match(text)
    if found is None:
        return 0
    parts = found.groupdict()
    return sum(int(parts[unit] or 0) * size for unit, size in UNIT_SECONDS.items())


def whole_number(value: object) -> int:
    text = str(value)
    return int(text) if text.isdigit() else 0


def part(value: object, key: str) -> dict[str, Any]:
    found = value.get(key) if isinstance(value, dict) else None
    return found if isinstance(found, dict) else {}


def listed(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def made_for_kids(status: dict[str, Any]) -> bool | None:
    flag = status.get("madeForKids")
    return flag if isinstance(flag, bool) else None


def trending_video(item: dict[str, Any]) -> TrendingVideo:
    snippet = part(item, "snippet")
    return TrendingVideo(
        title=str(snippet.get("title", "")),
        channel_title=str(snippet.get("channelTitle", "")),
        category_id=str(snippet.get("categoryId", "")),
        tags=tuple(str(tag) for tag in listed(snippet.get("tags"))),
        view_count=whole_number(part(item, "statistics").get("viewCount", 0)),
        duration_seconds=duration_seconds(str(part(item, "contentDetails").get("duration", ""))),
        made_for_kids=made_for_kids(part(item, "status")),
    )


def trending_videos(response: object) -> list[TrendingVideo]:
    items = listed(response.get("items") if isinstance(response, dict) else None)
    found = [trending_video(item) for item in items if isinstance(item, dict)]
    return [video for video in found if video.title.strip()]
