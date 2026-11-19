from __future__ import annotations

from typing import Any

from autotube.pipelines.narrated_video.template.definition import NarratedDefinition


def definition_fields() -> list[dict[str, Any]]:
    return list(NarratedDefinition.model_json_schema()["properties"].values())


def shown_texts() -> list[str]:
    fields = definition_fields()
    choices = [entry["title"] for field in fields for entry in field.get("oneOf", [])]
    return [*(f"{field['title']} {field['description']}" for field in fields), *choices]


def test_the_definition_never_says_engine() -> None:
    assert [text for text in shown_texts() if "engine" in text.casefold()] == []
