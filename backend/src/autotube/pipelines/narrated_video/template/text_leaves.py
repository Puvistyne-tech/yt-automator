from __future__ import annotations

from pydantic import JsonValue


def text_leaves(value: JsonValue) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in text_leaves(item)]
    if isinstance(value, list):
        return [text for item in value for text in text_leaves(item)]
    return []
