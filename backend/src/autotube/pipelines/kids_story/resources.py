from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from string import Template

PACKAGE = "autotube.pipelines.kids_story"


@cache
def resource_text(folder: str, name: str) -> str:
    return files(PACKAGE).joinpath(folder, name).read_text(encoding="utf-8")


def resource_json(folder: str, name: str) -> object:
    return json.loads(resource_text(folder, name))


def resource_names(folder: str, suffix: str) -> list[str]:
    return sorted(
        entry.name
        for entry in files(PACKAGE).joinpath(folder).iterdir()
        if entry.name.endswith(suffix)
    )


def render_prompt(template_name: str, /, **values: object) -> str:
    template = Template(resource_text("prompts", template_name))
    return template.safe_substitute({key: str(value) for key, value in values.items()}).strip()
