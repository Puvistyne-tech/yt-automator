from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides
from tests.unit.api.client import Api, error_of, ok, wired

STRUCTURES = ["story", "explainer", "list"]


@pytest.fixture
def narrated(config: RuntimeConfig, overrides: Overrides) -> Iterator[Api]:
    with wired(config, overrides, pipelines=None) as client:
        yield Api(client, client.app.state.runtime)  # type: ignore[attr-defined]


def body_for(structure: str) -> dict[str, Any]:
    return {
        "engine": "narrated_video",
        "name": "Sky facts",
        "audience": "general",
        "status": "ready",
        "definition": {"structure": structure},
    }


def other_structure(structure: str) -> str:
    return next(item for item in STRUCTURES if item != structure)


def assert_structure_fixed(api: Api, made: dict[str, Any], structure: str) -> None:
    path = f"/api/templates/{made['id']}"
    changed = api.client.put(path, json=body_for(other_structure(structure)))
    assert list(error_of(changed, 400)["fields"]) == ["definition.structure"]
    assert ok(api.client.get(path)) == made


@pytest.mark.parametrize("structure", STRUCTURES)
def test_changing_a_narrated_templates_structure_is_refused(narrated: Api, structure: str) -> None:
    made = ok(narrated.client.post("/api/templates", json=body_for(structure)), 201)
    assert_structure_fixed(narrated, made, structure)


@pytest.mark.parametrize("structure", STRUCTURES)
def test_a_duplicate_keeps_the_structure_and_still_refuses_a_change(
    narrated: Api, structure: str
) -> None:
    made = ok(narrated.client.post("/api/templates", json=body_for(structure)), 201)
    copy = ok(narrated.client.post(f"/api/templates/{made['id']}/duplicate"), 201)
    assert copy["definition"]["structure"] == structure
    assert_structure_fixed(narrated, copy, structure)
