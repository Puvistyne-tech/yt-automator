from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from string import Template

from autotube.domain.model_base import JsonObject

PACKAGE = "autotube.pipelines.narrated_video"


@cache
def resource_text(folder: str, name: str) -> str:
    return files(PACKAGE).joinpath(folder, name).read_text(encoding="utf-8")


def resource_json(folder: str, name: str) -> object:
    return json.loads(resource_text(folder, name))


def resource_object(folder: str, name: str) -> JsonObject:
    loaded = resource_json(folder, name)
    return loaded if isinstance(loaded, dict) else {}


def resource_names(folder: str, suffix: str) -> list[str]:
    return sorted(
        entry.name
        for entry in files(PACKAGE).joinpath(folder).iterdir()
        if entry.name.endswith(suffix)
    )


def render_prompt(template_name: str, /, **values: object) -> str:
    template = Template(resource_text("prompts", template_name))
    return template.safe_substitute({key: str(value) for key, value in values.items()}).strip()
