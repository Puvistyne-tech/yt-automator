from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from autotube.domain.capabilities import TextGenerator
from autotube.domain.template_suggestions import SUGGESTION_COUNT_MAX
from autotube.domain.trends import TrendingVideo
from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides
from tests.fixtures.fake_providers import WriterCatalog
from tests.fixtures.fake_youtube import FakeYouTube
from tests.fixtures.suggestion_data import idea_dict, ideas_writer, placeholder_writer
from tests.unit.api.client import Api, error_of, ok, wired

PATH = "/api/templates/suggestions"
SUGGESTION_KEYS = {"name", "description", "reason", "based_on", "input"}


def body(**changes: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {"engine": "narrated_video", "audience": "general", "region": "GB"}
    return fields | changes


@contextmanager
def served(
    config: RuntimeConfig, overrides: Overrides, writer: TextGenerator | None
) -> Iterator[TestClient]:
    with wired(config, overrides, pipelines=None, catalog=WriterCatalog(writer)) as client:
        yield client


def assert_nothing_stored(client: TestClient) -> None:
    assert [t["id"] for t in ok(client.get("/api/templates"))] == ["kids_story"]


def test_without_a_channel_suggestions_come_from_the_sample(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    with served(config, overrides, ideas_writer(idea_dict(), idea_dict(based_on=[99]))) as client:
        result = ok(client.post(PATH, json=body()))
        assert_nothing_stored(client)
    assert (result["source"], result["dropped"], result["provider"]) == ("sample", 1, "fake-llm")
    [suggestion] = result["suggestions"]
    assert set(suggestion) == SUGGESTION_KEYS
    assert suggestion["based_on"] == ["Ten minute pantry dinners for busy weeknights"]
    assert suggestion["input"] == {
        "engine": "narrated_video",
        "name": "Cupboard cooking",
        "description": "Quick meals from what is already at home.",
        "audience": "general",
        "status": "draft",
        "origin": "suggested",
        "definition": {"structure": "explainer", "brief": "Simple meals from cupboard staples."},
    }


def test_a_suggestion_saves_through_the_create_route(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    with served(config, overrides, ideas_writer(idea_dict())) as client:
        [suggestion] = ok(client.post(PATH, json=body()))["suggestions"]
        created = ok(client.post("/api/templates", json=suggestion["input"]), 201)
    assert (created["origin"], created["status"]) == ("suggested", "draft")


def test_a_connected_channel_supplies_youtube_trends(
    config: RuntimeConfig, overrides: Overrides, youtube: FakeYouTube
) -> None:
    with served(config, overrides, ideas_writer(idea_dict())) as client:
        Api(client, client.app.state.runtime).channel()  # type: ignore[attr-defined]
        response = client.post(PATH, json=body(category="26"))
    result = ok(response)
    assert result["source"] == "youtube"
    assert result["suggestions"][0]["based_on"] == ["Folding paper boats"]
    [query] = youtube.queries
    assert (query.region, query.category) == ("GB", "26")
    assert "csecret" not in response.text
    assert "token-for" not in response.text


def test_a_kids_request_yields_kids_drafts(config: RuntimeConfig, overrides: Overrides) -> None:
    kids_idea = idea_dict(name="Kitchen songs", definition={})
    with served(config, overrides, ideas_writer(kids_idea)) as client:
        [suggestion] = ok(client.post(PATH, json=body(audience="kids")))["suggestions"]
        created = ok(client.post("/api/templates", json=suggestion["input"]), 201)
    assert (suggestion["input"]["audience"], created["audience"]) == ("kids", "kids")


@pytest.mark.parametrize("count", [1, SUGGESTION_COUNT_MAX])
def test_the_count_bounds_are_accepted_and_reach_the_writer(
    config: RuntimeConfig, overrides: Overrides, count: int
) -> None:
    writer = ideas_writer(idea_dict())
    with served(config, overrides, writer) as client:
        ok(client.post(PATH, json=body(count=count)))
    [request] = writer.requests
    assert request.json_schema is not None
    assert request.json_schema["properties"]["ideas"]["maxItems"] == count  # type: ignore[index, call-overload]


def test_a_chart_of_only_kids_videos_has_nothing_for_a_general_request(
    config: RuntimeConfig, overrides: Overrides, youtube: FakeYouTube
) -> None:
    youtube.popular = [TrendingVideo(title="Counting ducks", made_for_kids=True)]
    with served(config, overrides, ideas_writer(idea_dict())) as client:
        Api(client, client.app.state.runtime).channel()  # type: ignore[attr-defined]
        conflict = error_of(client.post(PATH, json=body()), 409)
    assert conflict["code"] == "suggestions_unavailable"
    assert conflict["message"].startswith("No trending videos fit this audience")


@pytest.mark.parametrize(
    ("changes", "fields"),
    [
        ({"region": "gb"}, ["region"]),
        ({"count": 0}, ["count"]),
        ({"count": SUGGESTION_COUNT_MAX + 1}, ["count"]),
        ({"category": "music"}, ["category"]),
        ({"audience": "teens"}, ["audience"]),
        ({"engine": "missing"}, ["engine"]),
        ({"engine": ""}, ["engine"]),
    ],
)
def test_bad_fields_are_refused_without_asking_the_writer(
    config: RuntimeConfig, overrides: Overrides, changes: dict[str, Any], fields: list[str]
) -> None:
    writer = ideas_writer(idea_dict())
    with served(config, overrides, writer) as client:
        refused = error_of(client.post(PATH, json=body(**changes)), 400)
    assert sorted(refused["fields"]) == fields
    assert writer.requests == []


@pytest.mark.parametrize(
    ("writer", "message"),
    [
        (None, "The text model is not available"),
        (ideas_writer(idea_dict(name="Fun cooking for kids")), "None of the suggested ideas"),
        (placeholder_writer(idea_dict()), "Connect a text model under Providers"),
    ],
)
def test_no_usable_ideas_is_suggestions_unavailable(
    config: RuntimeConfig, overrides: Overrides, writer: TextGenerator | None, message: str
) -> None:
    with served(config, overrides, writer) as client:
        conflict = error_of(client.post(PATH, json=body()), 409)
        assert_nothing_stored(client)
    assert conflict["code"] == "suggestions_unavailable"
    assert conflict["message"].startswith(message)
