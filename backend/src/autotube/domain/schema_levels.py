from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

SchemaLevel = Literal["full", "portable"]
UNPORTABLE = frozenset({"prefixItems", "const", "minLength", "maxLength"})
SHAPE_SIZES = frozenset({"minItems", "maxItems"})


def portable_node(node: Any, dropped: frozenset[str]) -> Any:
    if isinstance(node, list):
        return [portable_node(item, dropped) for item in node]
    if not isinstance(node, Mapping):
        return node
    kept = {key: portable_node(value, dropped) for key, value in node.items() if key not in dropped}
    shapes = node.get("prefixItems")
    if isinstance(shapes, list) and shapes:
        kept["items"] = portable_node(shapes[0], dropped | SHAPE_SIZES)
    return kept


def schema_at(schema: Mapping[str, Any], level: SchemaLevel) -> dict[str, Any]:
    if level == "full":
        return dict(schema)
    return dict(portable_node(schema, UNPORTABLE))
