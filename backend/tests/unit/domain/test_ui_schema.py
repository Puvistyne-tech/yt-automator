from __future__ import annotations

import pytest
from pydantic import JsonValue

from automator.domain.model_base import JsonObject
from automator.domain.ui_schema import UI_WIDGETS, ui_schema_problems

SETTINGS: JsonObject = {
    "type": "object",
    "properties": {
        "series": {"$ref": "#/$defs/Series"},
        "cast": {"type": "array", "items": {"$ref": "#/$defs/Member"}},
    },
    "$defs": {
        "Series": {
            "type": "object",
            "properties": {"name": {"$ref": "#/$defs/Text"}, "style": {"type": "string"}},
        },
        "Text": {"type": "object", "properties": {"en": {"type": "string"}}},
        "Member": {
            "type": "object",
            "properties": {"palette": {"type": "array", "items": {"type": "string"}}},
        },
    },
}


def section(title: str, *fields: str) -> JsonValue:
    names: list[JsonValue] = list(fields)
    return {"title": title, "fields": names}


SECTIONS: list[JsonValue] = [section("Series", "series"), section("Cast", "cast")]
VALID: JsonObject = {
    "ui:sections": SECTIONS,
    "series": {
        "ui:order": ["style", "*"],
        "style": {"ui:widget": "textarea", "ui:options": {"rows": 3}},
        "name": {"en": {"ui:widget": "textarea"}},
    },
    "cast": {"items": {"palette": {"items": {"ui:widget": "color"}}}},
}


def test_a_ui_schema_following_the_contract_has_no_problems() -> None:
    assert ui_schema_problems(VALID, SETTINGS) == []


def test_the_contract_lists_the_widgets_the_form_registers() -> None:
    assert {"textarea", "select", "radio", "checkboxes", "range", "color"} == UI_WIDGETS


@pytest.mark.parametrize(
    ("ui", "problem"),
    [
        ({"ui:sections": "all"}, "ui:sections must be a list"),
        ({"ui:sections": [{"title": "Series"}]}, "section 0 needs a title and a list of fields"),
        ({"ui:sections": [*SECTIONS, section("More", "series")]}, "series is in more than one"),
        ({"ui:sections": [*SECTIONS, section("X", "nope")]}, "section field nope is not a setting"),
        ({"ui:sections": SECTIONS[:1]}, "cast is in no section"),
        ({"ui:sections": SECTIONS, "series": {"style": {"ui:widget": "slider"}}}, "slider"),
        ({"ui:sections": SECTIONS, "series": {"ui:order": ["nope"]}}, "series.ui:order"),
        ({"ui:sections": SECTIONS, "series": {"ui:order": "style"}}, "series.ui:order"),
        ({"ui:sections": SECTIONS, "series": {"ui:options": 3}}, "series.ui:options"),
        ({"ui:sections": SECTIONS, "series": {"ui:help": "x"}}, "series.ui:help"),
        ({"ui:sections": SECTIONS, "series": {"nope": {}}}, "series.nope"),
        ({"ui:sections": SECTIONS, "series": {"style": "textarea"}}, "series.style"),
        ({"ui:sections": SECTIONS, "series": {"items": {}}}, "series.items"),
        ({"ui:sections": SECTIONS, "cast": {"items": {"nope": {}}}}, "cast.items.nope"),
    ],
)
def test_each_contract_breach_is_named(ui: JsonObject, problem: str) -> None:
    assert any(problem in found for found in ui_schema_problems(ui, SETTINGS))


def test_an_empty_ui_schema_leaves_the_form_ungrouped_and_is_valid() -> None:
    assert ui_schema_problems({}, SETTINGS) == []
