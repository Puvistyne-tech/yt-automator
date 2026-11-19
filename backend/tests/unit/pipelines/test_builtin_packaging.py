from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from pydantic import JsonValue, ValidationError

from autotube.domain.model_base import JsonObject
from autotube.pipelines.narrated_video.engine import ENGINE_ID
from autotube.pipelines.narrated_video.template import builtins
from autotube.pipelines.narrated_video.template.builtins import (
    DuplicateBuiltinError,
    PackagedTemplate,
    packaged_entries,
    packaged_templates,
)
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.mapping import definition_settings
from autotube.pipelines.narrated_video.template.merging import deep_merged
from autotube.pipelines.narrated_video.template.settings_model import template_defaults

Path = tuple[str, ...]
MISSING = object()
VALID_ENTRY: dict[str, Any] = {
    "id": "facts",
    "name": "N",
    "description": "D.",
    "audience": "general",
    "definition": {},
}


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


@pytest.fixture
def fresh_cache() -> Iterator[None]:
    packaged_entries.cache_clear()
    yield
    packaged_entries.cache_clear()


def test_a_valid_entry_becomes_a_builtin_template() -> None:
    assert PackagedTemplate.model_validate(VALID_ENTRY).template(ENGINE_ID).type_id == "facts"


@pytest.mark.parametrize(
    "change",
    [
        {"extra": 1},
        {"id": "Facts"},
        {"id": "1x"},
        {"id": "a-b"},
        {"id": "t_x"},
        {"name": ""},
        {"description": ""},
        {"audience": "adults"},
    ],
)
def test_a_malformed_packaged_entry_is_refused(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PackagedTemplate.model_validate(VALID_ENTRY | change)


@pytest.mark.usefixtures("fresh_cache")
def test_two_packaged_files_with_one_id_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builtins, "resource_names", lambda *_: ["a.json", "b.json"])
    monkeypatch.setattr(builtins, "resource_json", lambda *_: VALID_ENTRY)
    with pytest.raises(DuplicateBuiltinError, match="'facts'"):
        packaged_templates(ENGINE_ID)
