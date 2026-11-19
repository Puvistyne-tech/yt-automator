from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError


class StoryFormatError(ValueError):
    pass


def json_object_text(raw: str) -> str:
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise StoryFormatError("answer with one JSON object")
    return raw[start : end + 1]


def parse_model[Model: BaseModel](raw: str, model: type[Model]) -> Model:
    try:
        return model.model_validate(json.loads(json_object_text(raw)))
    except json.JSONDecodeError as error:
        raise StoryFormatError(f"the JSON is invalid: {error.msg}") from error
    except ValidationError as error:
        details = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        raise StoryFormatError(f"the JSON does not match the shape: {details}") from error
