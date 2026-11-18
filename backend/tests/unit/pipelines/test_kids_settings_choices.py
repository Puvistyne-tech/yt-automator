from __future__ import annotations

from enum import Enum
from typing import Any, Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

from automator.pipelines.kids_story.settings.choices import titled_choices
from automator.pipelines.kids_story.settings.root import KidsStorySettings

SCHEMA = KidsStorySettings.model_json_schema()
Path = tuple[str | int, ...]


def allowed_values(annotation: Any) -> list[str] | None:
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return [str(member.value) for member in annotation]
    if get_origin(annotation) is Literal:
        return [str(getattr(value, "value", value)) for value in get_args(annotation)]
    return None


def nested_steps(annotation: Any) -> list[tuple[Path, type[BaseModel]]]:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [((), annotation)]
    is_list = get_origin(annotation) is list
    return [
        ((0,) if is_list else (), arg)
        for arg in get_args(annotation)
        if isinstance(arg, type) and issubclass(arg, BaseModel)
    ]


def choice_fields(model: type[BaseModel], prefix: Path = ()) -> dict[Path, list[str]]:
    found: dict[Path, list[str]] = {}
    for name, field in model.model_fields.items():
        path = (*prefix, name)
        values = allowed_values(field.annotation)
        if values is not None:
            found[path] = values
        for step, nested in nested_steps(field.annotation):
            found |= choice_fields(nested, (*path, *step))
    return found


CHOICES = choice_fields(KidsStorySettings)
PATHS = sorted(CHOICES, key=str)


def resolved(schema: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if reference is None:
        return schema
    target: dict[str, Any] = SCHEMA["$defs"][reference.rsplit("/", 1)[-1]]
    return target


def property_schema(path: Path) -> dict[str, Any]:
    node: dict[str, Any] = SCHEMA
    for step in path:
        container = resolved(node)
        node = container["items"] if isinstance(step, int) else container["properties"][step]
    return node


def with_value(path: Path, value: str) -> dict[str, Any]:
    data: dict[str, Any] = KidsStorySettings().model_dump(mode="json")
    node: Any = data
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value
    return data


def label(path: Path) -> str:
    return ".".join(str(step) for step in path)


def test_choice_fields_cover_known_paths() -> None:
    assert {("short", "scene_selection"), ("story", "source"), ("metadata", "category")} <= set(
        CHOICES
    )


@pytest.mark.parametrize("path", PATHS, ids=label)
def test_choice_field_offers_titled_options_for_exactly_its_values(path: Path) -> None:
    schema = property_schema(path)
    assert "enum" not in schema and "$ref" not in schema and "allOf" not in schema
    assert schema["type"] == "string"
    assert [option["const"] for option in schema["oneOf"]] == CHOICES[path]
    assert all(option["title"] for option in schema["oneOf"])


@pytest.mark.parametrize("path", PATHS, ids=label)
def test_choice_field_accepts_every_titled_value(path: Path) -> None:
    for option in property_schema(path)["oneOf"]:
        KidsStorySettings.model_validate(with_value(path, option["const"]))


@pytest.mark.parametrize("path", PATHS, ids=label)
def test_choice_field_rejects_a_value_outside_its_titles(path: Path) -> None:
    with pytest.raises(ValidationError):
        KidsStorySettings.model_validate(with_value(path, "not-a-choice"))


def test_titled_choices_replace_the_enum_with_titled_constants() -> None:
    schema: dict[str, Any] = {"$ref": "#/$defs/Mode", "enum": ["a"], "default": "a"}

    titled_choices({"a": "Alpha", "b": "Beta"})(schema)

    assert schema == {
        "default": "a",
        "type": "string",
        "oneOf": [{"const": "a", "title": "Alpha"}, {"const": "b", "title": "Beta"}],
    }
