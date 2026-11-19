from __future__ import annotations

from pydantic import JsonValue

from autotube.domain.json_schema import Schema, property_schema, resolve_ref, resolved
from autotube.domain.model_base import JsonObject
from autotube.domain.ui_basic import BASIC_KEY, basic_problems

UI_WIDGETS = frozenset({"textarea", "select", "radio", "checkboxes", "range", "color", "cards"})
CARDS_WIDGET = "cards"
CHOICE_GROUP_KEY = "x-group"
CHOICE_SWATCHES_KEY = "x-swatches"
MACHINE_LOCAL_KEY = "x-machine-local"
SECTIONS_KEY = "ui:sections"
ORDER_KEY = "ui:order"
WIDGET_KEY = "ui:widget"
OPTIONS_KEY = "ui:options"
UI_PREFIX = "ui:"
ORDER_WILDCARD = "*"
ROOT_ONLY_KEYS = frozenset({SECTIONS_KEY, BASIC_KEY})


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


def offers_choices(node: Schema) -> bool:
    return isinstance(node.get("oneOf"), list) or isinstance(node.get("enum"), list)


def widget_problems(value: JsonValue, has_choices: bool, path: str) -> list[str]:
    if not isinstance(value, str) or value not in UI_WIDGETS:
        return [f"{path} names unknown widget {value}"]
    if value == CARDS_WIDGET and not has_choices:
        return [f"{path} uses the cards widget on a setting without choices"]
    return []


def ui_key_problems(
    key: str, value: JsonValue, node: Schema, has_choices: bool, path: str
) -> list[str]:
    if key == WIDGET_KEY:
        return widget_problems(value, has_choices, path)
    if key == ORDER_KEY:
        return order_problems(value, node, path)
    if key == OPTIONS_KEY:
        return [] if isinstance(value, dict) else [f"{path} must be an object"]
    return [f"{path} is not a key the ui_schema contract lists"]


def entry_problems(
    key: str, value: JsonValue, schema: Schema, root: Schema, path: str
) -> list[str]:
    node = resolved(schema, root)
    if key.startswith(UI_PREFIX):
        return ui_key_problems(key, value, node, offers_choices(resolve_ref(schema, root)), path)
    child = property_schema(node, key, root, items=True)
    if child is None:
        return [f"{path} is not a setting"]
    if not isinstance(value, dict):
        return [f"{path} must be an object"]
    return node_problems(value, child, root, path)


def node_problems(ui: JsonObject, schema: Schema, root: Schema, path: str) -> list[str]:
    return [
        problem
        for key, value in ui.items()
        for problem in entry_problems(key, value, schema, root, joined(path, key))
    ]


def ui_schema_problems(ui_schema: JsonObject, settings_schema: JsonObject) -> list[str]:
    body = {key: value for key, value in ui_schema.items() if key not in ROOT_ONLY_KEYS}
    return [
        *section_problems(ui_schema, property_names(settings_schema)),
        *basic_problems(ui_schema, settings_schema),
        *node_problems(body, settings_schema, settings_schema, ""),
    ]
