from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from autotube.domain.json_schema import Schema, resolved
from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_descriptors import PipelineDescriptor
from autotube.domain.ui_schema import MACHINE_LOCAL_KEY

FieldPath = tuple[str, ...]
MISSING = object()


def object_properties(node: Schema) -> dict[str, Any]:
    properties = node.get("properties")
    return dict(properties) if isinstance(properties, Mapping) else {}


def machine_local_paths(
    schema: Schema, root: Schema | None = None, prefix: FieldPath = ()
) -> list[FieldPath]:
    top = schema if root is None else root
    paths: list[FieldPath] = []
    for name, child in object_properties(resolved(schema, top)).items():
        node = resolved(child, top) if isinstance(child, Mapping) else {}
        if node.get(MACHINE_LOCAL_KEY) is True:
            paths.append((*prefix, name))
        elif object_properties(node):
            paths.extend(machine_local_paths(node, top, (*prefix, name)))
    return paths


def value_at(source: Any, path: Sequence[str]) -> Any:
    node = source
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return MISSING
        node = node[key]
    return node


def reset_to_default(settings: JsonObject, path: FieldPath, defaults: JsonObject) -> None:
    parent = value_at(settings, path[:-1])
    if not isinstance(parent, dict):
        return
    fallback = value_at(defaults, path)
    if fallback is MISSING:
        parent.pop(path[-1], None)
    else:
        parent[path[-1]] = copy.deepcopy(fallback)


def with_local_defaults(settings: JsonObject, schema: Schema, defaults: JsonObject) -> JsonObject:
    portable = copy.deepcopy(settings)
    for path in machine_local_paths(schema):
        reset_to_default(portable, path, defaults)
    return portable


def portable_settings(settings: JsonObject, descriptor: PipelineDescriptor | None) -> JsonObject:
    if descriptor is None:
        return settings
    return with_local_defaults(settings, descriptor.settings_schema, descriptor.default_settings)
