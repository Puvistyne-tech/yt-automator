from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from autotube.domain.capabilities import TextRequest
from autotube.domain.trends import TrendingVideo, TrendQuery
from tests.fixtures.fake_providers import PLACEHOLDER_LLM
from tests.fixtures.kids_fakes import FakeWriter

TRENDS = (
    TrendingVideo(
        title="Ten minute pantry dinners",
        channel_title="Weeknight Kitchen",
        category_id="26",
        tags=("cooking", "quick meals"),
        view_count=1840000,
        duration_seconds=612,
        made_for_kids=False,
    ),
    TrendingVideo(
        title="Why the sky changes colour",
        channel_title="Curious Lab",
        category_id="28",
        tags=("science",),
        view_count=2210000,
        duration_seconds=498,
    ),
)


def idea_dict(**changes: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "name": "Cupboard cooking",
        "description": "Quick meals from what is already at home.",
        "reason": "Short practical cooking videos are popular right now.",
        "based_on": [1],
        "definition": {"structure": "explainer", "brief": "Simple meals from cupboard staples."},
    }
    return fields | changes


def ideas_reply(*ideas: dict[str, Any]) -> str:
    return json.dumps({"ideas": list(ideas)})


def raw_writer(answer: str) -> FakeWriter:
    def respond(request: TextRequest) -> str:
        del request
        return answer

    return FakeWriter(respond)


def ideas_writer(*ideas: dict[str, Any]) -> FakeWriter:
    return raw_writer(ideas_reply(*ideas))


class StaticTrends:
    def __init__(self, videos: Sequence[TrendingVideo] = TRENDS) -> None:
        self.videos = list(videos)
        self.queries: list[TrendQuery] = []

    def trending(self, query: TrendQuery) -> list[TrendingVideo]:
        self.queries.append(query)
        return list(self.videos)


def placeholder_writer(*ideas: dict[str, Any]) -> FakeWriter:
    writer = ideas_writer(*ideas)
    writer.provider_id = PLACEHOLDER_LLM.provider_id
    return writer
