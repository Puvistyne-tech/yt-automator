from __future__ import annotations

import pytest
from pydantic import JsonValue

from autotube.domain.model_base import JsonObject
from autotube.domain.ui_hidden import HIDDEN_KEY, hidden_problems
from autotube.domain.ui_schema import ui_schema_problems
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline

SETTINGS: JsonObject = {
    "type": "object",
    "required": ["title", "series", "voice", "music"],
    "properties": {
        "title": {"type": "string"},
        "series": {"$ref": "#/$defs/Series"},
        "cast": {"type": "array", "items": {"$ref": "#/$defs/Member"}},
        "extra": {"anyOf": [{"$ref": "#/$defs/Text"}, {"type": "null"}], "default": None},
        "mood": {"type": "string", "default": "calm"},
        "voice": {"$ref": "#/$defs/Voice"},
        "music": {"$ref": "#/$defs/Music", "default": {"enabled": True, "volume": 0.3}},
        "sound": {"anyOf": [{"$ref": "#/$defs/Sound"}, {"type": "null"}], "default": None},
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
        "Voice": {"type": "string", "default": "warm"},
        "Music": {
            "type": "object",
            "required": ["enabled", "volume"],
            "properties": {"enabled": {"type": "boolean"}, "volume": {"type": "number"}},
        },
        "Sound": {
            "type": "object",
            "required": ["level"],
            "properties": {"level": {"type": "number"}},
        },
    },
}
REQUIRED = "is required and has no default"


def problems_for(**keys: JsonValue) -> list[str]:
    return ui_schema_problems(dict(keys), SETTINGS)


def hiding(hidden: JsonValue, basic: JsonValue = None) -> list[str]:
    keys: dict[str, JsonValue] = {HIDDEN_KEY: hidden}
    return problems_for(**keys) if basic is None else problems_for(**keys, **{"ui:basic": basic})


def test_a_ui_schema_without_hidden_paths_has_no_hidden_problems() -> None:
    assert hidden_problems({}, SETTINGS) == []


def test_an_empty_hidden_list_is_valid() -> None:
    assert hiding([]) == []


@pytest.mark.parametrize(
    "hidden",
    [
        ["mood"],
        ["series.style", "series.name.en"],
        ["series.name"],
        ["extra", "cast"],
        ["extra.en"],
        ["voice"],
        ["music.volume"],
        ["music"],
    ],
)
def test_hidden_paths_that_can_be_filled_have_no_problems(hidden: JsonValue) -> None:
    assert hiding(hidden) == []


def test_hidden_is_a_root_only_key() -> None:
    assert problems_for(series={"ui:hidden": ["style"]}) == [
        "series.ui:hidden is not a key the ui_schema contract lists"
    ]


def test_hidden_entries_follow_the_shared_path_list_rules() -> None:
    assert hiding("mood") == ["ui:hidden must be a list"]
    assert hiding(["nope", 3, "cast.items", "mood", "mood"]) == [
        "ui:hidden path nope is not a setting",
        "ui:hidden entry 1 must be a dotted settings path",
        "ui:hidden path cast.items is not a setting",
        "ui:hidden names mood more than once",
    ]


@pytest.mark.parametrize(
    ("hidden", "problems"),
    [
        (["title"], [f"ui:hidden path title {REQUIRED}"]),
        (["series.code"], [f"ui:hidden path series.code {REQUIRED}"]),
        (["series"], [f"ui:hidden path series {REQUIRED}"]),
        (["sound.level"], [f"ui:hidden path sound.level {REQUIRED}"]),
        (
            ["title", "title"],
            ["ui:hidden names title more than once", f"ui:hidden path title {REQUIRED}"],
        ),
    ],
)
def test_a_hidden_setting_nothing_fills_is_named(hidden: JsonValue, problems: list[str]) -> None:
    assert hiding(hidden) == problems


@pytest.mark.parametrize(
    ("basic", "hidden", "problems"),
    [
        (["mood"], ["mood"], ["ui:basic and ui:hidden both name mood"]),
        (
            ["series.name.en"],
            ["series.name"],
            ["ui:basic path series.name.en lies under ui:hidden path series.name"],
        ),
        (
            ["series.name"],
            ["series.name.en"],
            ["ui:basic path series.name shows nothing because all of it is hidden"],
        ),
        (
            ["series"],
            ["series.style", "series.name"],
            [],
        ),
        (["series.styles"], ["series.style"], ["ui:basic path series.styles is not a setting"]),
    ],
)
def test_basic_paths_must_show_something_outside_hidden_paths(
    basic: JsonValue, hidden: JsonValue, problems: list[str]
) -> None:
    assert hiding(hidden, basic) == problems


def test_a_malformed_basic_list_is_not_compared_with_hidden_paths() -> None:
    assert hiding(["mood"], "mood") == ["ui:basic must be a list"]


def test_the_kids_story_pipeline_hides_the_pins_and_other_structures_counts() -> None:
    hidden = KidsStoryPipeline().descriptor.ui_schema[HIDDEN_KEY]
    assert hidden == [
        "safety.audience",
        "story.structure",
        "story.preview_attempts",
        "story.item_count",
        "story.quiz_questions",
        "story.answer_choices",
    ]
