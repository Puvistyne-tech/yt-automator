from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

Schema = Mapping[str, Any]
LOCAL_REFERENCE = "#/"
BRANCH_KEYS = ("anyOf", "oneOf", "allOf")


def resolve_ref(schema: Schema, root: Schema) -> dict[str, Any]:
    reference = schema.get("$ref")
    if not isinstance(reference, str) or not reference.startswith(LOCAL_REFERENCE):
        return dict(schema)
    node: Any = root
    for part in reference[len(LOCAL_REFERENCE) :].split("/"):
        node = node.get(part, {}) if isinstance(node, Mapping) else {}
    target = node if isinstance(node, Mapping) else {}
    return {**target, **{key: value for key, value in schema.items() if key != "$ref"}}


def non_null(options: Sequence[Any]) -> dict[str, Any]:
    branches = [item for item in options if isinstance(item, Mapping)]
    candidates = [item for item in branches if item.get("type") != "null"] or branches
    return dict(candidates[0]) if candidates else {}


def narrowed(schema: Schema) -> dict[str, Any]:
    for key in BRANCH_KEYS:
        options = schema.get(key)
        if isinstance(options, list) and options:
            return {**schema, **non_null(options), key: None}
    return dict(schema)


def resolved(schema: Schema, root: Schema) -> dict[str, Any]:
    return resolve_ref(narrowed(resolve_ref(schema, root)), root)
