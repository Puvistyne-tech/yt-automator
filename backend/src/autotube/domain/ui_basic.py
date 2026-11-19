from __future__ import annotations

from autotube.domain.json_schema import Schema
from autotube.domain.model_base import JsonObject
from autotube.domain.ui_paths import path_list_problems

BASIC_KEY = "ui:basic"


def basic_problems(ui_schema: JsonObject, settings_schema: Schema) -> list[str]:
    if BASIC_KEY not in ui_schema:
        return []
    raw = ui_schema[BASIC_KEY]
    if raw == []:
        return [f"{BASIC_KEY} must not be empty"]
    return path_list_problems(BASIC_KEY, raw, settings_schema)
