from __future__ import annotations

from collections.abc import Callable, Sequence

from pydantic import JsonValue

from autotube.domain.model_base import JsonObject
from autotube.pipelines.narrated_video.settings.series import (
    BANNED_WORDS,
    BRAND_NAMES,
    NO_HARM_RULE,
    PICTURE_EXCLUSIONS,
)

Floor = Callable[[JsonValue], JsonValue]


def listed_terms(text: str) -> list[str]:
    return [term.strip() for term in text.split(",") if term.strip()]


def list_floor(floor: Sequence[str]) -> Floor:
    def apply(value: JsonValue) -> JsonValue:
        if not isinstance(value, list):
            return value
        present = {item.casefold() for item in value if isinstance(item, str)}
        return [*value, *(item for item in floor if item.casefold() not in present)]

    return apply


def exclusions_floor(value: JsonValue) -> JsonValue:
    if not isinstance(value, str):
        return value
    present = {term.casefold() for term in listed_terms(value)}
    missing = [term for term in listed_terms(PICTURE_EXCLUSIONS) if term.casefold() not in present]
    return ", ".join([*listed_terms(value), *missing]) if missing else value


KIDS_FLOORS: dict[tuple[str, str], Floor] = {
    ("series", "editorial_rules"): list_floor([NO_HARM_RULE]),
    ("safety", "banned_words"): list_floor(BANNED_WORDS),
    ("safety", "brand_names"): list_floor(BRAND_NAMES),
    ("safety", "picture_exclusions"): exclusions_floor,
}


def floored_section(values: JsonObject, section: str, field: str, floor: Floor) -> JsonObject:
    current = values.get(section)
    if not isinstance(current, dict) or field not in current:
        return values
    return {**values, section: {**current, field: floor(current[field])}}


def kids_floor(values: JsonObject) -> JsonObject:
    floored = values
    for (section, field), floor in KIDS_FLOORS.items():
        floored = floored_section(floored, section, field, floor)
    return floored
