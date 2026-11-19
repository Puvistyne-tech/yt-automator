from __future__ import annotations

from autotube.domain.json_schema import Schema, property_schema, resolved
from autotube.domain.model_base import JsonObject
from autotube.domain.ui_basic import BASIC_KEY
from autotube.domain.ui_paths import listed_paths, path_list_problems, setting_at

HIDDEN_KEY = "ui:hidden"


def under(path: str, ancestor: str) -> bool:
    return path.startswith(f"{ancestor}.")


def basic_overlap(basic: str, hidden: list[str]) -> list[str]:
    if basic in hidden:
        return [f"{BASIC_KEY} and {HIDDEN_KEY} both name {basic}"]
    return [
        f"{BASIC_KEY} path {basic} lies under {HIDDEN_KEY} path {path}"
        for path in hidden
        if under(basic, path)
    ]


def overlap_problems(ui_schema: JsonObject, hidden: list[str]) -> list[str]:
    raw = ui_schema.get(BASIC_KEY)
    if not isinstance(raw, list):
        return []
    return [problem for basic in listed_paths(raw) for problem in basic_overlap(basic, hidden)]


def unfillable(path: str, settings_schema: Schema) -> bool:
    parent_path, _, name = path.rpartition(".")
    parent = setting_at(parent_path, settings_schema) if parent_path else dict(settings_schema)
    if parent is None:
        return False
    required = resolved(parent, settings_schema).get("required")
    child = property_schema(parent, name, settings_schema)
    if child is None or not isinstance(required, list) or name not in required:
        return False
    return "default" not in child and "default" not in resolved(child, settings_schema)


def required_problems(hidden: list[str], settings_schema: Schema) -> list[str]:
    return [
        f"{HIDDEN_KEY} path {path} is required and has no default"
        for path in dict.fromkeys(hidden)
        if unfillable(path, settings_schema)
    ]


def hidden_problems(ui_schema: JsonObject, settings_schema: Schema) -> list[str]:
    if HIDDEN_KEY not in ui_schema:
        return []
    raw = ui_schema[HIDDEN_KEY]
    hidden = listed_paths(raw)
    return [
        *path_list_problems(HIDDEN_KEY, raw, settings_schema),
        *required_problems(hidden, settings_schema),
        *overlap_problems(ui_schema, hidden),
    ]
