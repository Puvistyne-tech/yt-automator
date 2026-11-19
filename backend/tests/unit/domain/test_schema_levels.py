from __future__ import annotations

from typing import Any

from autotube.domain.schema_levels import schema_at

OPENING = {"type": "object", "properties": {"kind": {"const": "open"}}, "required": ["kind"]}
ITEM: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"const": "item"},
        "choices": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3},
    },
}
SHAPED: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 80},
        "scenes": {"type": "array", "prefixItems": [OPENING, ITEM], "minItems": 2, "maxItems": 2},
    },
    "required": ["title", "scenes"],
}


def test_the_full_level_keeps_every_keyword() -> None:
    assert schema_at(SHAPED, "full") == SHAPED


def test_the_portable_level_keeps_required_fields_and_array_sizes() -> None:
    portable = schema_at(SHAPED, "portable")
    assert portable["required"] == ["title", "scenes"]
    scenes = portable["properties"]["scenes"]
    assert (scenes["minItems"], scenes["maxItems"]) == (2, 2)
    assert portable["properties"]["title"] == {"type": "string"}


def test_the_portable_level_turns_scene_shapes_into_one_open_item_schema() -> None:
    scenes = schema_at(SHAPED, "portable")["properties"]["scenes"]
    assert "prefixItems" not in scenes
    assert scenes["items"] == {"type": "object", "properties": {"kind": {}}, "required": ["kind"]}


def test_the_portable_level_leaves_plain_items_alone() -> None:
    choices = schema_at(ITEM, "portable")["properties"]["choices"]
    assert choices == ITEM["properties"]["choices"]
