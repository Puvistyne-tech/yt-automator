from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import JsonValue

Schema = Mapping[str, Any]


@dataclass(frozen=True)
class SampleContext:
    topic: str
    array_items: int
    root: Schema


@dataclass(frozen=True)
class Slot:
    name: str
    index: int


def resolve_ref(schema: Schema, root: Schema) -> Schema:
    reference = schema.get("$ref")
    if not isinstance(reference, str) or not reference.startswith("#/"):
        return schema
    node: Any = root
    for part in reference[2:].split("/"):
        node = node.get(part, {}) if isinstance(node, Mapping) else {}
    return {**node, **{key: value for key, value in schema.items() if key != "$ref"}}


def preset(schema: Schema, slot: Slot) -> tuple[bool, JsonValue]:
    if "const" in schema:
        return True, schema["const"]
    if "default" in schema:
        return True, schema["default"]
    examples = schema.get("examples")
    if isinstance(examples, list) and examples:
        return True, examples[slot.index % len(examples)]
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return True, enum[slot.index % len(enum)]
    return False, None


def non_null(options: Any) -> Schema:
    candidates = [item for item in options if item.get("type") != "null"] or list(options)
    return dict(candidates[0]) if candidates else {}


def narrowed(schema: Schema) -> Schema:
    for key in ("anyOf", "oneOf", "allOf"):
        if isinstance(schema.get(key), list) and schema[key]:
            return {**schema, **non_null(schema[key]), key: None}
    return schema


def kind_of(schema: Schema) -> str:
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next((item for item in kind if item != "null"), "null")
    if kind is None:
        kind = "object" if "properties" in schema else "array" if "items" in schema else "string"
    return str(kind)


def humanised(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").strip().capitalize() or "Value"


def string_sample(schema: Schema, slot: Slot, context: SampleContext) -> JsonValue:
    ordinal = f" {slot.index + 1}" if slot.index else ""
    text = f"{humanised(slot.name)}{ordinal} about {context.topic}".strip()
    minimum = int(schema.get("minLength", 0))
    while len(text) < minimum:
        text = f"{text} {context.topic or 'and more'}"
    maximum = schema.get("maxLength")
    return text[: int(maximum)] if maximum is not None else text


def number_sample(schema: Schema, slot: Slot, context: SampleContext) -> JsonValue:
    del slot, context
    low = schema.get("minimum", schema.get("exclusiveMinimum", 1))
    high = schema.get("maximum", schema.get("exclusiveMaximum", low))
    value = low if low == high else (low + high) / 2
    return round(value) if kind_of(schema) == "integer" else float(value)


def object_sample(schema: Schema, slot: Slot, context: SampleContext) -> JsonValue:
    properties = schema.get("properties", {})
    return {
        name: sample(child, context, Slot(name, slot.index)) for name, child in properties.items()
    }


def array_sample(schema: Schema, slot: Slot, context: SampleContext) -> JsonValue:
    count = max(int(schema.get("minItems", 0)), context.array_items)
    if "maxItems" in schema:
        count = min(count, int(schema["maxItems"]))
    item = schema.get("items", {})
    name = slot.name[:-1] if slot.name.endswith("s") else slot.name
    return [sample(item, context, Slot(name, index)) for index in range(count)]


def boolean_sample(schema: Schema, slot: Slot, context: SampleContext) -> JsonValue:
    del schema, slot, context
    return True


def null_sample(schema: Schema, slot: Slot, context: SampleContext) -> JsonValue:
    del schema, slot, context
    return None


Sampler = Callable[[Schema, Slot, SampleContext], JsonValue]
SAMPLERS: dict[str, Sampler] = {
    "string": string_sample,
    "integer": number_sample,
    "number": number_sample,
    "object": object_sample,
    "array": array_sample,
    "boolean": boolean_sample,
    "null": null_sample,
}


def sample(schema: Schema, context: SampleContext, slot: Slot) -> JsonValue:
    resolved = resolve_ref(narrowed(resolve_ref(schema, context.root)), context.root)
    found, value = preset(resolved, slot)
    if found:
        return value
    return SAMPLERS.get(kind_of(resolved), string_sample)(resolved, slot, context)


def sample_document(schema: Schema, topic: str, array_items: int) -> JsonValue:
    context = SampleContext(topic=topic, array_items=array_items, root=schema)
    return sample(schema, context, Slot("value", 0))
