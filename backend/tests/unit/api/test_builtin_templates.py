from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides
from tests.fixtures.builtin_catalog import BUILTIN_IDS, KIDS_STORY, PACKAGED_FORMATS
from tests.unit.api.client import error_of, ok, wired

PACKAGED = list(PACKAGED_FORMATS)


class BuiltinIds:
    def new(self) -> str:
        return KIDS_STORY


@pytest.fixture
def client(config: RuntimeConfig, overrides: Overrides) -> Iterator[TestClient]:
    with wired(config, overrides, pipelines=None) as served:
        yield served


def test_templates_list_every_builtin_in_a_stable_order(client: TestClient) -> None:
    listed = ok(client.get("/api/templates"))
    assert [item["id"] for item in listed] == BUILTIN_IDS
    assert {item["origin"] for item in listed} == {"builtin"}
    assert all(item["builtin"] and item["status"] == "ready" for item in listed)
    pipelines = {item["type_id"] for item in ok(client.get("/api/pipelines"))}
    assert set(BUILTIN_IDS) <= pipelines


@pytest.mark.parametrize("template_id", PACKAGED)
def test_a_builtin_cannot_be_edited_or_deleted(client: TestClient, template_id: str) -> None:
    path = f"/api/templates/{template_id}"
    current = ok(client.get(path))
    body = {key: current[key] for key in ("engine", "name", "audience", "status", "definition")}
    assert error_of(client.put(path, json=body | {"name": "Mine"}), 409)["code"] == (
        "template_builtin"
    )
    assert error_of(client.delete(path), 409)["code"] == "template_builtin"
    assert ok(client.get(path)) == current


@pytest.mark.parametrize("template_id", PACKAGED)
def test_a_builtin_duplicates_into_an_editable_draft(client: TestClient, template_id: str) -> None:
    source = ok(client.get(f"/api/templates/{template_id}"))
    copy = ok(client.post(f"/api/templates/{template_id}/duplicate"), 201)
    assert (copy["origin"], copy["status"], copy["builtin"]) == ("duplicate", "draft", False)
    assert copy["type_id"] == f"t_{copy['id']}" and copy["id"] not in BUILTIN_IDS
    assert (copy["definition"], copy["audience"]) == (source["definition"], source["audience"])
    renamed = {**copy, "name": "My copy", "status": "ready"}
    body = {key: renamed[key] for key in ("engine", "name", "audience", "status", "definition")}
    saved = ok(client.put(f"/api/templates/{copy['id']}", json=body))
    assert (saved["name"], saved["revision"]) == ("My copy", 2)


def test_creating_a_template_with_a_builtin_id_is_a_conflict(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    body = {"engine": "narrated_video", "name": "Mine", "audience": "general", "definition": {}}
    with wired(config, overrides, pipelines=None, ids=BuiltinIds()) as client:
        refused = client.post("/api/templates", json=body)
        assert error_of(refused, 409)["code"] == "template_exists"
        assert [item["id"] for item in ok(client.get("/api/templates"))] == BUILTIN_IDS
