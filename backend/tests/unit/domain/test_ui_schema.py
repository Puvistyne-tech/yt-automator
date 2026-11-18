from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import JsonValue

from autotube.domain.model_base import JsonObject
from autotube.domain.ui_schema import UI_WIDGETS, ui_schema_problems

SPEC = Path(__file__).resolve().parents[4] / "docs" / "spec" / "platform.md"
WIDGET_LINE = "- `ui:widget`: one of "
SETTINGS: JsonObject = {
    "type": "object",
    "properties": {
        "series": {"$ref": "#/$defs/Series"},
        "cast": {"type": "array", "items": {"$ref": "#/$defs/Member"}},
        "extra": {"anyOf": [{"$ref": "#/$defs/Text"}, {"type": "null"}], "default": None},
        "lost": {"$ref": "#/$defs/Gone"},
    },
    "$defs": {
        "Series": {
            "type": "object",
            "properties": {
                "name": {"$ref": "#/$defs/Text"},
                "style": {"type": "string"},
                "look": {"type": "string", "oneOf": [{"const": "a", "title": "A", "x-group": "G"}]},
                "tone": {"type": "string", "enum": ["calm", "funny"]},
            },
        },
        "Text": {"type": "object", "properties": {"en": {"type": "string"}}},
        "Member": {
            "type": "object",
            "properties": {"palette": {"type": "array", "items": {"type": "string"}}},
        },
    },
}


def section(title: JsonValue, fields: JsonValue) -> JsonValue:
    return {"title": title, "fields": fields}


SECTIONS: list[JsonValue] = [
    section("Series", ["series", "extra"]),
    section("Cast", ["cast", "lost"]),
]
VALID: JsonObject = {
    "ui:sections": SECTIONS,
    "series": {
        "ui:order": ["style", "*"],
        "style": {"ui:widget": "textarea", "ui:options": {"rows": 3}},
        "name": {"en": {"ui:widget": "textarea"}},
        "look": {"ui:widget": "cards"},
        "tone": {"ui:widget": "cards"},
    },
    "cast": {"items": {"palette": {"items": {"ui:widget": "color"}}}},
    "extra": {"en": {"ui:widget": "textarea"}},
}


def spec_widgets() -> set[str]:
    line = next(line for line in SPEC.read_text().splitlines() if WIDGET_LINE in line)
    listed = line.split(WIDGET_LINE, 1)[1].split("(", 1)[0]
    return set(re.findall(r"`([a-z]+)`", listed))


def with_sections(**hints: JsonValue) -> JsonObject:
    return {"ui:sections": SECTIONS, **hints}


def test_a_ui_schema_following_the_contract_has_no_problems() -> None:
    assert ui_schema_problems(VALID, SETTINGS) == []


def test_the_spec_lists_exactly_the_contract_widgets() -> None:
    assert spec_widgets() == UI_WIDGETS


def test_an_empty_ui_schema_leaves_the_form_ungrouped_and_is_valid() -> None:
    assert ui_schema_problems({}, SETTINGS) == []


@pytest.mark.parametrize(
    ("ui", "problems"),
    [
        ({"ui:sections": "all"}, ["ui:sections must be a list"]),
        (
            {"ui:sections": [*SECTIONS, section("Series", None)]},
            ["section 2 needs a title and a list of fields"],
        ),
        (
            {"ui:sections": [*SECTIONS, section(1, [])]},
            ["section 2 needs a title and a list of fields"],
        ),
        (
            {"ui:sections": [*SECTIONS, section("T", "series")]},
            ["section 2 needs a title and a list of fields"],
        ),
        (
            {"ui:sections": [*SECTIONS, section("T", [1])]},
            ["section 2 needs a title and a list of fields"],
        ),
        (
            {"ui:sections": [*SECTIONS, section("More", ["series"])]},
            ["series is in more than one section"],
        ),
        (
            {"ui:sections": [*SECTIONS, section("X", ["nope"])]},
            ["section field nope is not a setting"],
        ),
        (
            {"ui:sections": SECTIONS[:1]},
            ["cast is in no section", "lost is in no section"],
        ),
    ],
)
def test_each_section_breach_is_named(ui: JsonObject, problems: list[str]) -> None:
    assert ui_schema_problems(ui, SETTINGS) == problems


@pytest.mark.parametrize(
    ("hints", "problems"),
    [
        (
            {"series": {"style": {"ui:widget": "slider"}}},
            ["series.style.ui:widget names unknown widget slider"],
        ),
        (
            {"series": {"style": {"ui:widget": "cards"}}},
            ["series.style.ui:widget uses the cards widget on a setting without choices"],
        ),
        (
            {"series": {"style": {"ui:widget": 3}}},
            ["series.style.ui:widget names unknown widget 3"],
        ),
        (
            {"series": {"style": {"ui:widget": ["range"]}}},
            ["series.style.ui:widget names unknown widget ['range']"],
        ),
        (
            {"series": {"ui:order": ["nope", "*"]}},
            ["series.ui:order names unknown field nope"],
        ),
        (
            {"series": {"ui:order": [1, "*"]}},
            ["series.ui:order names unknown field 1"],
        ),
        (
            {"series": {"ui:order": ["style", "look", "tone"]}},
            ["series.ui:order leaves out name"],
        ),
        ({"series": {"ui:order": ["style", "name", "look", "tone"]}}, []),
        ({"series": {"ui:order": "style"}}, ["series.ui:order must be a list"]),
        ({"series": {"ui:options": 3}}, ["series.ui:options must be an object"]),
        (
            {"series": {"ui:help": "x"}},
            ["series.ui:help is not a key the ui_schema contract lists"],
        ),
        ({"series": {"nope": {}}}, ["series.nope is not a setting"]),
        ({"series": {"style": "textarea"}}, ["series.style must be an object"]),
        ({"series": {"items": {}}}, ["series.items is not a setting"]),
        ({"cast": {"items": {"nope": {}}}}, ["cast.items.nope is not a setting"]),
        ({"lost": {"en": {}}}, ["lost.en is not a setting"]),
        ({"extra": {"fr": {}}}, ["extra.fr is not a setting"]),
    ],
)
def test_each_hint_breach_is_named(hints: JsonObject, problems: list[str]) -> None:
    assert ui_schema_problems(with_sections(**hints), SETTINGS) == problems
