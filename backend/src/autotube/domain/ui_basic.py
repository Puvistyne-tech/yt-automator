from __future__ import annotations

from typing import Any

from pydantic import JsonValue

from autotube.domain.json_schema import Schema, resolved
from autotube.domain.model_base import JsonObject

BASIC_KEY = "ui:basic"


def property_at(node: Schema, key: str, root: Schema) -> dict[str, Any] | None:
    properties = resolved(node, root).get("properties")
    if not isinstance(properties, dict) or not isinstance(properties.get(key), dict):
        return None
    return dict(properties[key])


def resolves_to_setting(path: str, settings_schema: Schema) -> bool:
    node: dict[str, Any] | None = dict(settings_schema)
    for key in path.split("."):
        node = None if node is None else property_at(node, key, settings_schema)
    return node is not None


def entry_problem(index: int, entry: JsonValue, settings_schema: Schema) -> list[str]:
    if not isinstance(entry, str):
        return [f"{BASIC_KEY} entry {index} must be a dotted settings path"]
    if not resolves_to_setting(entry, settings_schema):
        return [f"{BASIC_KEY} path {entry} is not a setting"]
    return []


def repeated_paths(entries: list[JsonValue]) -> list[str]:
    paths = [entry for entry in entries if isinstance(entry, str)]
    return [
        f"{BASIC_KEY} names {path} more than once"
        for path in sorted(set(paths))
        if paths.count(path) > 1
    ]


def basic_problems(ui_schema: JsonObject, settings_schema: Schema) -> list[str]:
    if BASIC_KEY not in ui_schema:
        return []
    raw = ui_schema[BASIC_KEY]
    if not isinstance(raw, list):
        return [f"{BASIC_KEY} must be a list"]
    return [
        *(
            problem
            for index, entry in enumerate(raw)
            for problem in entry_problem(index, entry, settings_schema)
        ),
        *repeated_paths(raw),
    ]
