from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from automator.domain.capabilities import TextRequest
from automator.domain.model_base import JsonObject
from automator.infrastructure.providers.llm.gemini import GeminiOptions, GeminiText
from automator.infrastructure.providers.llm.groq import GroqOptions, GroqText
from automator.infrastructure.providers.llm.ollama import OllamaOptions, OllamaText
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import make_context

SCHEMA: JsonObject = {"type": "object", "properties": {"title": {"type": "string"}}}


class Recorder:
    def __init__(self, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responses.pop(0)

    def body(self, index: int = 0) -> dict[str, object]:
        loaded: dict[str, object] = json.loads(self.requests[index].content)
        return loaded


def chat_reply(text: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def test_groq_posts_chat_completion_with_json_schema(tmp_path: Path) -> None:
    recorder = Recorder(chat_reply('{"title": "x"}'))
    context = make_context(tmp_path, handler=recorder, secrets={"groq_api_key": "sk-test"})
    request = TextRequest(prompt="Tell a story", system="Be kind", json_schema=SCHEMA)
    reply = GroqText(GroqOptions(), context).generate(request)
    sent = recorder.requests[0]
    assert reply == '{"title": "x"}'
    assert str(sent.url) == "https://api.groq.com/openai/v1/chat/completions"
    assert sent.headers["authorization"] == "Bearer sk-test"
    assert recorder.body() == {
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "system", "content": "Be kind"},
            {"role": "user", "content": "Tell a story"},
        ],
        "max_tokens": 1024,
        "temperature": 0.7,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "response", "schema": SCHEMA},
        },
    }


def test_groq_json_object_mode_and_plain_text(tmp_path: Path) -> None:
    recorder = Recorder(chat_reply("{}"), chat_reply("hi"))
    context = make_context(tmp_path, handler=recorder, secrets={"groq_api_key": "k"})
    adapter = GroqText(GroqOptions(structured_output="json_object"), context)
    adapter.generate(TextRequest(prompt="p", json_schema=SCHEMA))
    adapter.generate(TextRequest(prompt="p"))
    assert recorder.body(0)["response_format"] == {"type": "json_object"}
    assert "response_format" not in recorder.body(1)


def test_groq_retries_rate_limits_with_backoff(tmp_path: Path) -> None:
    sleeps: list[float] = []
    recorder = Recorder(
        httpx.Response(429, headers={"retry-after": "5"}),
        httpx.Response(503),
        chat_reply("ok"),
    )
    context = make_context(tmp_path, handler=recorder, secrets={"groq_api_key": "k"}, sleeps=sleeps)
    reply = GroqText(GroqOptions(backoff_seconds=1.0), context).generate(TextRequest(prompt="p"))
    assert reply == "ok"
    assert sleeps == [5.0, 2.0]


def test_groq_gives_up_after_retries_and_hides_the_key(tmp_path: Path) -> None:
    recorder = Recorder(*(httpx.Response(500, text="boom") for _ in range(3)))
    context = make_context(tmp_path, handler=recorder, secrets={"groq_api_key": "secret-key"})
    adapter = GroqText(GroqOptions(max_retries=2), context)
    with pytest.raises(UpstreamFailure) as raised:
        adapter.generate(TextRequest(prompt="p"))
    assert "HTTP 500" in raised.value.message
    assert "secret-key" not in raised.value.message
    assert len(recorder.requests) == 3


def test_groq_does_not_retry_client_errors(tmp_path: Path) -> None:
    recorder = Recorder(httpx.Response(401, text="bad key"))
    context = make_context(tmp_path, handler=recorder, secrets={"groq_api_key": "k"})
    with pytest.raises(UpstreamFailure, match="HTTP 401"):
        GroqText(GroqOptions(), context).generate(TextRequest(prompt="p"))
    assert len(recorder.requests) == 1


def test_groq_needs_its_secret_and_rejects_images(tmp_path: Path) -> None:
    adapter = GroqText(GroqOptions(), make_context(tmp_path))
    assert adapter.available() == "set the Groq API key secret (groq_api_key)"
    with pytest.raises(UpstreamFailure, match="image input"):
        adapter.generate(TextRequest(prompt="p", images=(tmp_path / "a.png",)))


def test_groq_wraps_network_errors(tmp_path: Path) -> None:
    context = make_context(tmp_path, secrets={"groq_api_key": "k"})
    with pytest.raises(UpstreamFailure, match="ConnectError"):
        GroqText(GroqOptions(max_retries=0), context).generate(TextRequest(prompt="p"))


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


def test_ollama_availability_checks_server_and_model(tmp_path: Path) -> None:
    down = OllamaText(OllamaOptions(), make_context(tmp_path))
    assert "not running" in (down.available() or "")
    tags = httpx.Response(200, json={"models": [{"name": "gemma3:12b"}, {"name": "phi4:latest"}]})
    for model, expected in (("gemma3:12b", None), ("phi4", None), ("qwen3", "not pulled")):
        context = make_context(tmp_path, handler=Recorder(tags))
        reason = OllamaText(OllamaOptions(model=model), context).available()
        assert (reason is None) if expected is None else expected in (reason or "")
