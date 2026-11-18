from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.json_schema import narrowed, non_null, resolve_ref, resolved

ROOT: dict[str, Any] = {
    "$defs": {"Text": {"type": "string", "title": "Text"}, "Leaf": "not an object"},
}


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"$ref": "#/$defs/Text", "title": "Name"}, {"type": "string", "title": "Name"}),
        ({"$ref": "#/$defs/Gone"}, {}),
        ({"$ref": "#/$defs/Leaf"}, {}),
        ({"$ref": "#/$defs/Text/type/deeper"}, {}),
        ({"$ref": "other.json#/Text"}, {"$ref": "other.json#/Text"}),
        ({"type": "integer"}, {"type": "integer"}),
    ],
)
def test_resolve_ref_follows_local_references_and_keeps_sibling_keys(
    schema: dict[str, Any], expected: dict[str, Any]
) -> None:
    assert resolve_ref(schema, ROOT) == expected


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ([{"type": "null"}, {"type": "string"}], {"type": "string"}),
        ([{"type": "null"}], {"type": "null"}),
        (["text", {"type": "integer"}], {"type": "integer"}),
        ([], {}),
    ],
)
def test_non_null_picks_the_first_branch_that_is_not_null(
    options: list[Any], expected: dict[str, Any]
) -> None:
    assert non_null(options) == expected


def test_resolved_follows_an_optional_reference_to_its_definition() -> None:
    optional = {"anyOf": [{"$ref": "#/$defs/Text"}, {"type": "null"}], "default": None}
    assert resolved(optional, ROOT) == {
        "type": "string",
        "title": "Text",
        "anyOf": None,
        "default": None,
    }
    assert narrowed({"oneOf": []}) == {"oneOf": []}
