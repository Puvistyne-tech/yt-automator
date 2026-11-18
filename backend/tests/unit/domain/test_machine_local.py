from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from autotube.domain.machine_local import machine_local_paths, with_local_defaults
from autotube.domain.pipeline_descriptors import default_settings_of, settings_schema_of
from autotube.domain.ui_schema import MACHINE_LOCAL_KEY

LOCAL: dict[str, Any] = {MACHINE_LOCAL_KEY: True}


class Fonts(BaseModel):
    family: str = "Sans"
    file: str = Field(default="", json_schema_extra=LOCAL)


class Branding(BaseModel):
    logo: str | None = Field(default=None, json_schema_extra=LOCAL)
    fonts: Fonts = Field(default_factory=Fonts)


class LocalSettings(BaseModel):
    title: str = "Story"
    music_folder: str = Field(default="/defaults/music", json_schema_extra=LOCAL)
    branding: Branding = Field(default_factory=Branding)
    optional_fonts: Fonts | None = None
    fonts_list: list[Fonts] = Field(default_factory=list)


SCHEMA = settings_schema_of(LocalSettings)
DEFAULTS = default_settings_of(LocalSettings)


def test_paths_follow_refs_and_optional_objects_but_not_lists() -> None:
    assert machine_local_paths(SCHEMA) == [
        ("music_folder",),
        ("branding", "logo"),
        ("branding", "fonts", "file"),
        ("optional_fonts", "file"),
    ]


def test_paths_of_a_schema_without_markers() -> None:
    assert machine_local_paths({"type": "object", "properties": {"a": {"type": "string"}}}) == []


def test_local_values_take_the_defaults_and_the_rest_is_kept() -> None:
    settings = LocalSettings(
        title="Mine",
        music_folder="/Users/me/music",
        branding=Branding(logo="/Users/me/logo.png", fonts=Fonts(family="Serif", file="/f.ttf")),
        optional_fonts=Fonts(file="/Users/me/x.ttf"),
    ).model_dump(mode="json")
    portable = with_local_defaults(settings, SCHEMA, DEFAULTS)
    assert portable["music_folder"] == "/defaults/music"
    assert portable["branding"] == {"logo": None, "fonts": {"family": "Serif", "file": ""}}
    assert portable["optional_fonts"] == {"family": "Sans"}
    assert portable["title"] == "Mine"
    assert settings["music_folder"] == "/Users/me/music"


def test_missing_parents_stay_missing() -> None:
    assert with_local_defaults({"title": "Only"}, SCHEMA, DEFAULTS) == {
        "title": "Only",
        "music_folder": "/defaults/music",
    }
