from __future__ import annotations

from typing import Any

TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "null": (type(None),),
    "array": (list,),
    "object": (dict,),
}


def resolved(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    found: dict[str, Any] = root["$defs"][ref.rsplit("/", 1)[-1]]
    return found


def type_misfits(schema: dict[str, Any], value: Any) -> list[str]:
    wanted = schema.get("type")
    if wanted is None:
        return []
    is_bool = isinstance(value, bool) and wanted != "boolean"
    return [] if isinstance(value, TYPES[wanted]) and not is_bool else [f"not {wanted}"]


def size_misfits(schema: dict[str, Any], value: Any) -> list[str]:
    if not isinstance(value, str | list):
        return []
    low = schema.get("minLength", schema.get("minItems", 0))
    high = schema.get("maxLength", schema.get("maxItems", len(value)))
    return [] if low <= len(value) <= high else [f"size {len(value)} not in {low}..{high}"]


def value_misfits(schema: dict[str, Any], value: Any) -> list[str]:
    if "const" in schema and value != schema["const"]:
        return [f"{value!r} is not {schema['const']!r}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{value!r} not in enum"]
    return []


def child_misfits(schema: dict[str, Any], value: Any, root: dict[str, Any]) -> list[str]:
    if isinstance(value, dict):
        missing = [f"missing {key}" for key in schema.get("required", []) if key not in value]
        props = schema.get("properties", {})
        nested = [
            m
            for key, item in value.items()
            if key in props
            for m in misfits(props[key], item, root)
        ]
        return [*missing, *nested]
    if isinstance(value, list):
        prefix = schema.get("prefixItems", [])
        items = [
            prefix[i] if i < len(prefix) else schema.get("items", {}) for i in range(len(value))
        ]
        return [
            m
            for item_schema, item in zip(items, value, strict=True)
            for m in misfits(item_schema, item, root)
        ]
    return []


def misfits(schema: dict[str, Any], value: Any, root: dict[str, Any] | None = None) -> list[str]:
    top = root or schema
    current = resolved(schema, top)
    if "anyOf" in current:
        options = [misfits(option, value, top) for option in current["anyOf"]]
        return [] if any(not found for found in options) else options[0]
    checks = (type_misfits, size_misfits, value_misfits)
    own = [m for check in checks for m in check(current, value)]
    return own or child_misfits(current, value, top)
