from __future__ import annotations

import pytest
from pydantic import JsonValue

from autotube.domain.model_base import JsonObject
from autotube.pipelines.narrated_video.template.builtins import PackagedTemplate, packaged_entries
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.mapping import definition_settings
from autotube.pipelines.narrated_video.template.merging import deep_merged
from autotube.pipelines.narrated_video.template.settings_model import template_defaults

Path = tuple[str, ...]
MISSING = object()


def leaves(value: JsonValue, path: Path = ()) -> dict[Path, JsonValue]:
    if not isinstance(value, dict) or not value:
        return {path: value}
    return {
        found: item
        for key, child in value.items()
        for found, item in leaves(child, (*path, key)).items()
    }


def value_at(values: JsonObject, path: Path) -> object:
    current: object = values
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return MISSING
        current = current[key]
    return current


def effective_overlay(definition: NarratedDefinition) -> JsonObject:
    return deep_merged(definition_settings(definition), definition.settings)


@pytest.mark.parametrize("entry", packaged_entries(), ids=lambda entry: entry.id)
def test_a_packaged_definition_sets_only_what_differs_from_the_defaults(
    entry: PackagedTemplate,
) -> None:
    blank = NarratedDefinition().model_dump(mode="json")
    assert [key for key, value in entry.definition.items() if blank.get(key) == value] == []
    definition = NarratedDefinition.model_validate(entry.definition)
    base = NarratedDefinition(structure=definition.structure)
    defaults = template_defaults(base, entry.audience)
    overlay = leaves(effective_overlay(definition))
    assert [path for path, value in overlay.items() if value_at(defaults, path) == value] == []
