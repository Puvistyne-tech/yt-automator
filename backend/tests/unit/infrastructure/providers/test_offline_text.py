from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from autotube.domain.capabilities import TextRequest
from autotube.infrastructure.providers.llm.json_sample import sample_document
from autotube.infrastructure.providers.llm.offline_text import OfflineText, OfflineTextOptions
from tests.unit.infrastructure.providers.fakes import make_context


class Scene(BaseModel):
    narration: str = Field(min_length=20, max_length=60)
    image_prompt: str
    camera: Literal["push_in", "pan_left"]
    seconds: float = Field(ge=2, le=6)


class Story(BaseModel):
    title: str = Field(max_length=30)
    moral: str | None = None
    age: int = Field(ge=3, le=7)
    scenes: list[Scene] = Field(min_length=4)
    tags: list[str] = Field(default_factory=list, max_length=2)
    safe: bool


def offline(tmp_path: Path, **options: int) -> OfflineText:
    return OfflineText(OfflineTextOptions.model_validate(options), make_context(tmp_path))


def test_schema_requests_get_a_valid_document(tmp_path: Path) -> None:
    schema = Story.model_json_schema()
    reply = offline(tmp_path).generate(
        TextRequest(prompt="A shy turtle learns to swim", json_schema=schema)
    )
    story = Story.model_validate_json(reply)
    assert len(story.scenes) == 4
    assert len(story.tags) == 2
    assert "shy turtle" in story.scenes[0].narration
    assert story.scenes[1].camera == "pan_left"
    assert story.age == 5


def test_output_is_deterministic(tmp_path: Path) -> None:
    request = TextRequest(prompt="A brave cat", json_schema=Story.model_json_schema())
    assert offline(tmp_path).generate(request) == offline(tmp_path).generate(request)


def test_plain_text_uses_template(tmp_path: Path) -> None:
    adapter = offline(tmp_path, topic_words=2)
    assert (
        adapter.generate(TextRequest(prompt="Moonlit forest walk."))
        == "Offline draft. Moonlit forest"
    )
    assert adapter.available() is None


def test_array_length_option_and_examples() -> None:
    schema = {
        "type": "array",
        "items": {"type": "string", "examples": ["one", "two"]},
        "maxItems": 5,
    }
    assert sample_document(schema, "x", 3) == ["one", "two", "one"]
    assert json.dumps(sample_document({"type": ["null", "integer"], "minimum": 2}, "x", 1)) == "2"
