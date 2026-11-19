from __future__ import annotations

from typing import Any

from pydantic import JsonValue

from autotube.domain.json_schema import Schema, property_schema


def setting_at(path: str, settings_schema: Schema) -> dict[str, Any] | None:
    node: dict[str, Any] | None = dict(settings_schema)
    for key in path.split("."):
        node = None if node is None else property_schema(node, key, settings_schema)
    return node


def resolves_to_setting(path: str, settings_schema: Schema) -> bool:
    return setting_at(path, settings_schema) is not None


def listed_paths(raw: JsonValue) -> list[str]:
    return [entry for entry in raw if isinstance(entry, str)] if isinstance(raw, list) else []


def entry_problem(key: str, index: int, entry: JsonValue, settings_schema: Schema) -> list[str]:
    if not isinstance(entry, str):
        return [f"{key} entry {index} must be a dotted settings path"]
    if not resolves_to_setting(entry, settings_schema):
        return [f"{key} path {entry} is not a setting"]
    return []


def repeated_paths(key: str, entries: list[JsonValue]) -> list[str]:
    paths = listed_paths(entries)
    return [
        f"{key} names {path} more than once" for path in sorted(set(paths)) if paths.count(path) > 1
    ]


def path_list_problems(key: str, raw: JsonValue, settings_schema: Schema) -> list[str]:
    if not isinstance(raw, list):
        return [f"{key} must be a list"]
    return [
        *(
            problem
            for index, entry in enumerate(raw)
            for problem in entry_problem(key, index, entry, settings_schema)
        ),
        *repeated_paths(key, raw),
    ]
