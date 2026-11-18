from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from autotube.domain.capabilities import TextRequest
from autotube.domain.model_base import JsonObject
from autotube.infrastructure.providers.llm.gemini import GeminiOptions, GeminiText
from autotube.infrastructure.providers.llm.ollama import OllamaOptions, OllamaText
from autotube.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import make_context
from tests.unit.infrastructure.providers.http_fakes import Recorder

SCHEMA: JsonObject = {"type": "object", "properties": {"title": {"type": "string"}}}


def test_gemini_sends_images_schema_and_key_header(tmp_path: Path) -> None:
    image = tmp_path / "scene.png"
    image.write_bytes(b"png-bytes")
    reply = {"candidates": [{"content": {"parts": [{"text": "a "}, {"text": "cat"}]}}]}
    recorder = Recorder(httpx.Response(200, json=reply))
    context = make_context(tmp_path, handler=recorder, secrets={"gemini_api_key": "g-key"})
    request = TextRequest(prompt="Describe", system="Short", json_schema=SCHEMA, images=(image,))
    assert GeminiText(GeminiOptions(), context).generate(request) == "a cat"
    sent = recorder.requests[0]
    assert sent.url.path == "/v1beta/models/gemini-2.5-flash:generateContent"
    assert sent.headers["x-goog-api-key"] == "g-key"
    assert "key" not in sent.url.params
    assert recorder.body() == {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Describe"},
                    {"inline_data": {"mime_type": "image/png", "data": "cG5nLWJ5dGVz"}},
                ],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 1024,
            "temperature": 0.7,
            "responseMimeType": "application/json",
            "responseJsonSchema": SCHEMA,
        },
        "systemInstruction": {"parts": [{"text": "Short"}]},
    }


def test_gemini_rejects_empty_candidates(tmp_path: Path) -> None:
    recorder = Recorder(httpx.Response(200, json={"candidates": []}))
    context = make_context(tmp_path, handler=recorder, secrets={"gemini_api_key": "g"})
    with pytest.raises(UpstreamFailure, match="missing"):
        GeminiText(GeminiOptions(), context).generate(TextRequest(prompt="p"))


def test_gemini_needs_its_secret(tmp_path: Path) -> None:
    adapter = GeminiText(GeminiOptions(), make_context(tmp_path))
    assert adapter.available() == "set the Gemini API key secret (gemini_api_key)"


def test_gemini_plain_request_retries_server_errors(tmp_path: Path) -> None:
    sleeps: list[float] = []
    reply = {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}
    recorder = Recorder(httpx.Response(503), httpx.Response(200, json=reply))
    context = make_context(
        tmp_path, handler=recorder, secrets={"gemini_api_key": "g"}, sleeps=sleeps
    )
    options = GeminiOptions(backoff_seconds=0.5)
    assert GeminiText(options, context).generate(TextRequest(prompt="p")) == "hi"
    assert sleeps == [0.5]
    assert recorder.body(1) == {
        "contents": [{"role": "user", "parts": [{"text": "p"}]}],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7},
    }


def test_ollama_chat_payload_with_images_and_format(tmp_path: Path) -> None:
    image = tmp_path / "a.png"
    image.write_bytes(b"img")
    recorder = Recorder(httpx.Response(200, json={"message": {"content": "seen"}}))
    context = make_context(tmp_path, handler=recorder)
    request = TextRequest(prompt="Look", json_schema=SCHEMA, images=(image,), max_tokens=50)
    assert OllamaText(OllamaOptions(model="llava"), context).generate(request) == "seen"
    assert str(recorder.requests[0].url) == "http://127.0.0.1:11434/api/chat"
    assert recorder.body() == {
        "model": "llava",
        "messages": [{"role": "user", "content": "Look", "images": ["aW1n"]}],
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 50},
        "format": SCHEMA,
    }


def test_ollama_is_not_running_without_a_server(tmp_path: Path) -> None:
    reason = OllamaText(OllamaOptions(), make_context(tmp_path)).available()
    assert "not running" in (reason or "")


@pytest.mark.parametrize(
    ("model", "reason"),
    [
        ("gemma3:12b", None),
        ("phi4", None),
        ("qwen3", "Ollama model 'qwen3' is not pulled (ollama pull it)"),
    ],
)
def test_ollama_availability_checks_the_model(
    tmp_path: Path, model: str, reason: str | None
) -> None:
    tags = httpx.Response(200, json={"models": [{"name": "gemma3:12b"}, {"name": "phi4:latest"}]})
    context = make_context(tmp_path, handler=Recorder(tags))
    assert OllamaText(OllamaOptions(model=model), context).available() == reason
