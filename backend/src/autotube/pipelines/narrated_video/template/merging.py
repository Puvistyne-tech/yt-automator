from __future__ import annotations

from autotube.domain.model_base import JsonObject


def deep_merged(base: JsonObject, overlay: JsonObject) -> JsonObject:
    merged = dict(base)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = deep_merged(current, value)
        else:
            merged[key] = value
    return merged


def merged_all(base: JsonObject, *overlays: JsonObject) -> JsonObject:
    merged = base
    for overlay in overlays:
        merged = deep_merged(merged, overlay)
    return merged
