from __future__ import annotations

from pydantic import JsonValue

from automator.domain.model_base import JsonObject

UI_WIDGETS = frozenset({"textarea", "select", "radio", "checkboxes", "range", "color"})
SECTIONS_KEY = "ui:sections"
ORDER_KEY = "ui:order"
WIDGET_KEY = "ui:widget"
OPTIONS_KEY = "ui:options"
UI_PREFIX = "ui:"
ITEMS_KEY = "items"
ORDER_WILDCARD = "*"


def as_object(value: JsonValue) -> JsonObject:
    return value if isinstance(value, dict) else {}


def resolved(node: JsonObject, root: JsonObject) -> JsonObject:
    reference = node.get("$ref")
    if not isinstance(reference, str):
        return node
    definitions = as_object(root.get("$defs"))
    return resolved(as_object(definitions.get(reference.rsplit("/", 1)[-1])), root)


def property_names(node: JsonObject) -> list[str]:
    return list(as_object(node.get("properties")))


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


def order_problems(value: JsonValue, node: JsonObject, path: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{path} must be a list"]
    names = property_names(node)
    return [
        f"{path} names unknown field {entry}"
        for entry in value
        if entry != ORDER_WILDCARD and entry not in names
    ]


def child_schema(key: str, node: JsonObject) -> JsonObject | None:
    if key == ITEMS_KEY and node.get("type") == "array":
        return as_object(node.get(ITEMS_KEY))
    properties = as_object(node.get("properties"))
    return as_object(properties[key]) if key in properties else None


def ui_key_problems(key: str, value: JsonValue, node: JsonObject, path: str) -> list[str]:
    if key == WIDGET_KEY:
        return [] if value in UI_WIDGETS else [f"{path} names unknown widget {value}"]
    if key == ORDER_KEY:
        return order_problems(value, node, path)
    if key == OPTIONS_KEY:
        return [] if isinstance(value, dict) else [f"{path} must be an object"]
    return [f"{path} is not a key the ui_schema contract lists"]


def entry_problems(
    key: str, value: JsonValue, node: JsonObject, root: JsonObject, path: str
) -> list[str]:
    if key.startswith(UI_PREFIX):
        return ui_key_problems(key, value, node, path)
    child = child_schema(key, node)
    if child is None:
        return [f"{path} is not a setting"]
    if not isinstance(value, dict):
        return [f"{path} must be an object"]
    return node_problems(value, child, root, path)


def node_problems(ui: JsonObject, schema: JsonObject, root: JsonObject, path: str) -> list[str]:
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
