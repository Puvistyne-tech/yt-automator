from __future__ import annotations

import pytest
from pydantic import JsonValue

from autotube.domain.model_base import JsonObject
from autotube.domain.ui_hidden import HIDDEN_KEY, hidden_problems
from autotube.domain.ui_schema import ui_schema_problems

SETTINGS: JsonObject = {
    "type": "object",
    "required": ["title", "series"],
    "properties": {
        "title": {"type": "string"},
        "series": {"$ref": "#/$defs/Series"},
        "cast": {"type": "array", "items": {"$ref": "#/$defs/Member"}},
        "extra": {"anyOf": [{"$ref": "#/$defs/Text"}, {"type": "null"}], "default": None},
        "mood": {"type": "string", "default": "calm"},
    },
    "$defs": {
        "Series": {
            "type": "object",
            "required": ["code", "style"],
            "properties": {
                "code": {"type": "string"},
                "style": {"type": "string", "default": "flat"},
                "name": {"$ref": "#/$defs/Text"},
            },
        },
        "Text": {"type": "object", "properties": {"en": {"type": "string"}}},
        "Member": {"type": "object", "properties": {"name": {"type": "string"}}},
    },
}


def problems_for(**keys: JsonValue) -> list[str]:
    return ui_schema_problems(dict(keys), SETTINGS)


def test_a_ui_schema_without_hidden_paths_has_no_hidden_problems() -> None:
    assert hidden_problems({}, SETTINGS) == []


def test_hidden_is_named_by_the_contract_key() -> None:
    assert HIDDEN_KEY == "ui:hidden"


@pytest.mark.parametrize(
    "hidden",
    [
        [],
        ["mood"],
        ["series.style", "series.name.en"],
        ["series.name"],
        ["extra", "cast"],
        ["extra.en"],
    ],
)
def test_hidden_paths_that_resolve_to_optional_settings_have_no_problems(
    hidden: JsonValue,
) -> None:
    assert problems_for(**{"ui:hidden": hidden}) == []


def test_hidden_is_a_root_only_key() -> None:
    assert problems_for(series={"ui:hidden": ["style"]}) == [
        "series.ui:hidden is not a key the ui_schema contract lists"
    ]


@pytest.mark.parametrize(
    ("hidden", "problems"),
    [
        ("mood", ["ui:hidden must be a list"]),
        (["mood", 3], ["ui:hidden entry 1 must be a dotted settings path"]),
        (["series.nope"], ["ui:hidden path series.nope is not a setting"]),
        (["cast.items"], ["ui:hidden path cast.items is not a setting"]),
        (["mood", "mood"], ["ui:hidden names mood more than once"]),
        (["title"], ["ui:hidden path title is required and has no default"]),
        (["series.code"], ["ui:hidden path series.code is required and has no default"]),
        (["series"], ["ui:hidden path series is required and has no default"]),
    ],
)
def test_each_hidden_breach_is_named(hidden: JsonValue, problems: list[str]) -> None:
    assert problems_for(**{"ui:hidden": hidden}) == problems


@pytest.mark.parametrize(
    ("basic", "hidden", "problems"),
    [
        (["mood"], ["mood"], ["ui:basic and ui:hidden both name mood"]),
        (
            ["series.name.en"],
            ["series.name"],
            ["ui:basic path series.name.en lies under ui:hidden path series.name"],
        ),
        (["series"], ["series.style"], []),
        (["series.styles"], ["series.style"], ["ui:basic path series.styles is not a setting"]),
    ],
)
def test_basic_paths_must_stay_outside_hidden_paths(
    basic: JsonValue, hidden: JsonValue, problems: list[str]
) -> None:
    assert problems_for(**{"ui:basic": basic, "ui:hidden": hidden}) == problems


def test_a_malformed_basic_list_is_not_compared_with_hidden_paths() -> None:
    hidden: JsonValue = ["mood"]
    assert problems_for(**{"ui:basic": "mood", "ui:hidden": hidden}) == ["ui:basic must be a list"]
