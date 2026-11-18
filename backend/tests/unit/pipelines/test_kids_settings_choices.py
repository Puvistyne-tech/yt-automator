from __future__ import annotations

from enum import Enum
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel

from automator.pipelines.kids_story.settings.choices import titled_choices
from automator.pipelines.kids_story.settings.root import KidsStorySettings

SCHEMA = KidsStorySettings.model_json_schema()


def allowed_values(annotation: Any) -> list[str] | None:
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return [str(member.value) for member in annotation]
    if get_origin(annotation) is Literal:
        return [str(getattr(value, "value", value)) for value in get_args(annotation)]
    return None


def nested_models(annotation: Any) -> list[type[BaseModel]]:
    candidates = [annotation, *get_args(annotation)]
    return [c for c in candidates if isinstance(c, type) and issubclass(c, BaseModel)]


def choice_fields(model: type[BaseModel]) -> dict[str, tuple[str, list[str]]]:
    found: dict[str, tuple[str, list[str]]] = {}
    for name, field in model.model_fields.items():
        values = allowed_values(field.annotation)
        if values is not None:
            found[f"{model.__name__}.{name}"] = (model.__name__, values)
        for nested in nested_models(field.annotation):
            found |= choice_fields(nested)
    return found


def property_schema(model_name: str, field_name: str) -> dict[str, Any]:
    definition = SCHEMA if model_name == SCHEMA["title"] else SCHEMA["$defs"][model_name]
    properties: dict[str, dict[str, Any]] = definition["properties"]
    return properties[field_name]


def test_every_choice_field_offers_titled_options_for_exactly_its_values() -> None:
    fields = choice_fields(KidsStorySettings)
    assert fields
    for path, (model_name, values) in fields.items():
        schema = property_schema(model_name, path.split(".")[1])
        assert "enum" not in schema and "$ref" not in schema, path
        options = schema["oneOf"]
        assert [option["const"] for option in options] == values, path
        assert all(option["title"] for option in options), path


def test_titled_choices_replace_the_enum_with_titled_constants() -> None:
    schema: dict[str, Any] = {"$ref": "#/$defs/Mode", "enum": ["a"], "default": "a"}

    titled_choices({"a": "Alpha", "b": "Beta"})(schema)

    assert schema == {
        "default": "a",
        "type": "string",
        "oneOf": [{"const": "a", "title": "Alpha"}, {"const": "b", "title": "Beta"}],
    }
