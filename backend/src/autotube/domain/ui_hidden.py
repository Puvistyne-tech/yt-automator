from __future__ import annotations

from typing import Any

from autotube.domain.json_schema import Schema, property_schema, resolved
from autotube.domain.model_base import JsonObject
from autotube.domain.setting_fill import unfillable
from autotube.domain.ui_basic import BASIC_KEY
from autotube.domain.ui_paths import listed_paths, path_list_problems, setting_at

HIDDEN_KEY = "ui:hidden"


def lies_under(path: str, ancestor: str) -> bool:
    return path.startswith(f"{ancestor}.")


def covered(path: str, hidden: list[str]) -> bool:
    return any(path == listed or lies_under(path, listed) for listed in hidden)


def emptied(path: str, node: dict[str, Any], hidden: list[str], root: Schema) -> bool:
    properties = resolved(node, root).get("properties")
    if not isinstance(properties, dict) or not properties:
        return covered(path, hidden)
    return all(
        emptied(f"{path}.{name}", property_schema(node, name, root) or {}, hidden, root)
        for name in properties
    )


def basic_overlap(basic: str, hidden: list[str], root: Schema) -> list[str]:
    if basic in hidden:
        return [f"{BASIC_KEY} and {HIDDEN_KEY} both name {basic}"]
    above = [path for path in hidden if lies_under(basic, path)]
    if above:
        return [f"{BASIC_KEY} path {basic} lies under {HIDDEN_KEY} path {path}" for path in above]
    node = setting_at(basic, root)
    if node is not None and emptied(basic, node, hidden, root):
        return [f"{BASIC_KEY} path {basic} shows nothing because all of it is hidden"]
    return []


def overlap_problems(ui_schema: JsonObject, hidden: list[str], root: Schema) -> list[str]:
    raw = ui_schema.get(BASIC_KEY)
    if not isinstance(raw, list):
        return []
    return [
        problem for basic in listed_paths(raw) for problem in basic_overlap(basic, hidden, root)
    ]


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
        *overlap_problems(ui_schema, hidden, settings_schema),
    ]
