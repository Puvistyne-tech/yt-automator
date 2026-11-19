from __future__ import annotations

from typing import Any

from autotube.domain.capabilities import TextRequest
from autotube.domain.model_base import JsonObject
from autotube.infrastructure.providers.llm.gemini import generation_config
from autotube.infrastructure.providers.llm.groq import response_format
from autotube.infrastructure.providers.llm.ollama import ollama_payload

SHAPED: JsonObject = {
    "type": "array",
    "prefixItems": [{"type": "object", "properties": {"kind": {"const": "open"}}}],
    "minItems": 1,
    "maxItems": 1,
}
PORTABLE: dict[str, Any] = {
    "type": "array",
    "items": {"type": "object", "properties": {"kind": {}}},
    "minItems": 1,
    "maxItems": 1,
}
REQUEST = TextRequest(prompt="p", json_schema=SHAPED)


def test_gemini_and_groq_receive_the_portable_schema() -> None:
    assert generation_config(REQUEST)["responseJsonSchema"] == PORTABLE
    groq = response_format(REQUEST, "json_schema")
    assert groq is not None and groq["json_schema"]["schema"] == PORTABLE


def test_ollama_receives_the_full_schema() -> None:
    assert ollama_payload(REQUEST, "qwen3", 4096)["format"] == SHAPED
