from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ValidationError

from automator.domain.model_base import JsonObject

ROOT_FIELD = "__root__"


def field_path(*parts: str | int) -> str:
    return ".".join(str(part) for part in parts if str(part) != "")


def field_errors(error: ValidationError, prefix: str = "") -> dict[str, str]:
    errors: dict[str, str] = {}
    for detail in error.errors():
        path = field_path(prefix, *detail["loc"]) or ROOT_FIELD
        errors.setdefault(path, detail["msg"])
    return errors


def prefixed(errors: Mapping[str, str], *prefix: str | int) -> dict[str, str]:
    return {field_path(*prefix, key): message for key, message in errors.items()}


def validated_settings(
    model: type[BaseModel], settings: JsonObject, prefix: str = "settings"
) -> tuple[BaseModel | None, dict[str, str]]:
    try:
        return model.model_validate(settings), {}
    except ValidationError as error:
        return None, field_errors(error, prefix)
