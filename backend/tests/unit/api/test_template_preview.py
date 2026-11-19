from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from autotube.domain.capabilities import TextGenerator
from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides
from tests.fixtures.explainer_data import TAKEAWAY_EN, explainer_writer
from tests.fixtures.fake_providers import WriterCatalog
from tests.fixtures.kids_data import draft_dict, smart_writer
from tests.unit.api.client import error_of, ok, wired

PATH = "/api/templates/preview-script"
SAMPLE_KEYS = {
    "language",
    "title",
    "scenes",
    "takeaway",
    "upload_title",
    "upload_description",
    "provider",
}


def body(**changes: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "engine": "narrated_video",
        "name": "Sky facts",
        "audience": "general",
        "definition": {"structure": "explainer"},
    }
    return fields | changes


@contextmanager
def served(
    config: RuntimeConfig, overrides: Overrides, writer: TextGenerator | None
) -> Iterator[TestClient]:
    with wired(config, overrides, pipelines=None, catalog=WriterCatalog(writer)) as client:
        yield client


def assert_nothing_stored(client: TestClient) -> None:
    assert [t["id"] for t in ok(client.get("/api/templates"))] == ["kids_story"]
    assert ok(client.get("/api/runs")) == []


def test_a_general_explainer_preview_returns_a_sample_and_stores_nothing(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    with served(config, overrides, explainer_writer()) as client:
        sample = ok(client.post(PATH, json=body()))
        assert set(sample) == SAMPLE_KEYS
        assert (sample["language"], sample["takeaway"], sample["provider"]) == (
            "en",
            TAKEAWAY_EN,
            "fake-llm",
        )
        assert set(sample["scenes"][0]) == {"narration", "heading", "action"}
        assert sample["upload_title"]
        assert_nothing_stored(client)


def test_a_kids_story_preview_takes_a_topic(config: RuntimeConfig, overrides: Overrides) -> None:
    writer = smart_writer()
    kids = body(audience="kids", definition={}, language="en", topic="sharing")
    with served(config, overrides, writer) as client:
        sample = ok(client.post(PATH, json=kids))
    assert (sample["title"], sample["takeaway"]) == (draft_dict()["title"], draft_dict()["moral"])
    assert "sharing" in writer.requests[0].prompt


@pytest.mark.parametrize(
    ("changes", "fields"),
    [
        ({"name": " "}, ["name"]),
        ({"definition": {"surprise": 1}}, ["definition.surprise"]),
        ({"language": "fr"}, ["language"]),
        ({"type_id": "t_mine"}, ["type_id"]),
    ],
)
def test_a_preview_returns_the_create_field_errors(
    config: RuntimeConfig, overrides: Overrides, changes: dict[str, Any], fields: list[str]
) -> None:
    writer = explainer_writer()
    with served(config, overrides, writer) as client:
        refused = error_of(client.post(PATH, json=body(**changes)), 400)
        assert_nothing_stored(client)
    assert sorted(refused["fields"]) == fields
    assert writer.requests == []


@pytest.mark.parametrize("audience", ["kids", "general"])
def test_a_missing_writer_is_preview_unavailable_without_a_bundled_story(
    config: RuntimeConfig, overrides: Overrides, audience: str
) -> None:
    with served(config, overrides, None) as client:
        conflict = error_of(client.post(PATH, json=body(audience=audience, definition={})), 409)
        assert_nothing_stored(client)
    assert conflict["code"] == "preview_unavailable"
    assert conflict["message"].startswith("The script writer is not available")
