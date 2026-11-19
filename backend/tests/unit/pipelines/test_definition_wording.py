from __future__ import annotations

from typing import Any

from autotube.pipelines.narrated_video.template.definition import NarratedDefinition

SHORT_SENTENCE = 90


def definition_fields() -> list[dict[str, Any]]:
    return list(NarratedDefinition.model_json_schema()["properties"].values())


def shown_texts() -> list[str]:
    fields = definition_fields()
    choices = [entry["title"] for field in fields for entry in field.get("oneOf", [])]
    return [*(f"{field['title']} {field['description']}" for field in fields), *choices]


def test_the_definition_never_says_engine() -> None:
    assert [text for text in shown_texts() if "engine" in text.casefold()] == []


def test_every_definition_field_is_described_in_one_short_sentence() -> None:
    descriptions = [field["description"] for field in definition_fields()]
    assert [text for text in descriptions if text.count(".") != 1 or not text.endswith(".")] == []
    assert [text for text in descriptions if len(text) > SHORT_SENTENCE] == []


def test_an_empty_style_keeps_the_default_style() -> None:
    style = NarratedDefinition.model_json_schema()["properties"]["visual_style"]
    assert style["oneOf"][0] == {"const": "", "title": "Keep the default style"}
