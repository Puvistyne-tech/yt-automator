from __future__ import annotations

from typing import Any

from pydantic import JsonValue

from automator.domain.json_schema import Schema, resolved
from automator.domain.model_base import JsonObject

UI_WIDGETS = frozenset({"textarea", "select", "radio", "checkboxes", "range", "color"})
SECTIONS_KEY = "ui:sections"
ORDER_KEY = "ui:order"
WIDGET_KEY = "ui:widget"
OPTIONS_KEY = "ui:options"
UI_PREFIX = "ui:"
ITEMS_KEY = "items"
ORDER_WILDCARD = "*"


def property_names(node: Schema) -> list[str]:
    properties = node.get("properties")
    return list(properties) if isinstance(properties, dict) else []


def joined(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def section_fields(section: JsonValue) -> list[str] | None:
    if not isinstance(section, dict) or not isinstance(section.get("title"), str):
        return None
    fields = section.get("fields")
    if not isinstance(fields, list) or not all(isinstance(field, str) for field in fields):
        return None
    return [str(field) for field in fields]


def placement_problems(placed: list[str], names: list[str]) -> list[str]:
    unknown = [f"section field {name} is not a setting" for name in placed if name not in names]
    repeated = [
        f"{name} is in more than one section"
        for name in sorted(set(placed))
        if placed.count(name) > 1
    ]
    missing = [f"{name} is in no section" for name in names if name not in placed]
    return [*unknown, *repeated, *missing]


def section_problems(ui_schema: JsonObject, names: list[str]) -> list[str]:
    if SECTIONS_KEY not in ui_schema:
        return []
    raw = ui_schema[SECTIONS_KEY]
    if not isinstance(raw, list):
        return [f"{SECTIONS_KEY} must be a list"]
    problems: list[str] = []
    placed: list[str] = []
    for index, section in enumerate(raw):
        fields = section_fields(section)
        if fields is None:
            problems.append(f"section {index} needs a title and a list of fields")
        else:
            placed.extend(fields)
    return [*problems, *placement_problems(placed, names)]


def order_problems(value: JsonValue, node: Schema, path: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{path} must be a list"]
    names = property_names(node)
    unknown = [
        f"{path} names unknown field {entry}"
        for entry in value
        if entry != ORDER_WILDCARD and entry not in names
    ]
    if ORDER_WILDCARD in value:
        return unknown
    return [*unknown, *(f"{path} leaves out {name}" for name in names if name not in value)]


def child_schema(key: str, node: Schema) -> dict[str, Any] | None:
    if key == ITEMS_KEY and node.get("type") == "array":
        items = node.get(ITEMS_KEY)
        return dict(items) if isinstance(items, dict) else {}
    properties = node.get("properties")
    if not isinstance(properties, dict) or key not in properties:
        return None
    child = properties[key]
    return dict(child) if isinstance(child, dict) else {}


def widget_problems(value: JsonValue, path: str) -> list[str]:
    if isinstance(value, str) and value in UI_WIDGETS:
        return []
    return [f"{path} names unknown widget {value}"]


def ui_key_problems(key: str, value: JsonValue, node: Schema, path: str) -> list[str]:
    if key == WIDGET_KEY:
        return widget_problems(value, path)
    if key == ORDER_KEY:
        return order_problems(value, node, path)
    if key == OPTIONS_KEY:
        return [] if isinstance(value, dict) else [f"{path} must be an object"]
    return [f"{path} is not a key the ui_schema contract lists"]


def entry_problems(key: str, value: JsonValue, node: Schema, root: Schema, path: str) -> list[str]:
    if key.startswith(UI_PREFIX):
        return ui_key_problems(key, value, node, path)
    child = child_schema(key, node)
    if child is None:
        return [f"{path} is not a setting"]
    if not isinstance(value, dict):
        return [f"{path} must be an object"]
    return node_problems(value, child, root, path)


def node_problems(ui: JsonObject, schema: Schema, root: Schema, path: str) -> list[str]:
    node = resolved(schema, root)
    return [
        problem
        for key, value in ui.items()
        for problem in entry_problems(key, value, node, root, joined(path, key))
    ]


def ui_schema_problems(ui_schema: JsonObject, settings_schema: JsonObject) -> list[str]:
    body = {key: value for key, value in ui_schema.items() if key != SECTIONS_KEY}
    return [
        *section_problems(ui_schema, property_names(settings_schema)),
        *node_problems(body, settings_schema, settings_schema, ""),
    ]
