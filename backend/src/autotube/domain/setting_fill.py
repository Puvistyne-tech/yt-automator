from __future__ import annotations

from typing import Any

from autotube.domain.json_schema import Schema, property_schema, resolved
from autotube.domain.ui_paths import setting_at

MISSING = object()


def own_default(node: dict[str, Any], settings_schema: Schema) -> Any:
    if "default" in node:
        return node["default"]
    return resolved(node, settings_schema).get("default", MISSING)


def value_below(value: Any, keys: list[str]) -> Any:
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return MISSING
        value = value[key]
    return value


def ancestor_fills(keys: list[str], settings_schema: Schema) -> bool:
    for depth in range(1, len(keys)):
        node = setting_at(".".join(keys[:depth]), settings_schema)
        default = MISSING if node is None else own_default(node, settings_schema)
        if value_below(default, keys[depth:]) is not MISSING:
            return True
    return False


def required_by_parent(keys: list[str], settings_schema: Schema) -> dict[str, Any] | None:
    parent_path, name = ".".join(keys[:-1]), keys[-1]
    parent = setting_at(parent_path, settings_schema) if parent_path else dict(settings_schema)
    if parent is None:
        return None
    required = resolved(parent, settings_schema).get("required")
    if not isinstance(required, list) or name not in required:
        return None
    return property_schema(parent, name, settings_schema)


def unfillable(path: str, settings_schema: Schema) -> bool:
    keys = path.split(".")
    child = required_by_parent(keys, settings_schema)
    if child is None or own_default(child, settings_schema) is not MISSING:
        return False
    return not ancestor_fills(keys, settings_schema)
