from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from automator.domain.capabilities import TextRequest
from automator.domain.model_base import JsonObject
from automator.infrastructure.providers.llm.groq import GroqOptions, GroqText
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import make_context
from tests.unit.infrastructure.providers.http_fakes import Recorder, chat_reply, groq_context

SCHEMA: JsonObject = {"type": "object", "properties": {"title": {"type": "string"}}}


def test_groq_posts_chat_completion_with_json_schema(tmp_path: Path) -> None:
    recorder = Recorder(chat_reply('{"title": "x"}'))
    context = groq_context(tmp_path, recorder, key="sk-test")
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
    context = groq_context(tmp_path, recorder)
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
    context = groq_context(tmp_path, recorder, sleeps)
    reply = GroqText(GroqOptions(backoff_seconds=1.0), context).generate(TextRequest(prompt="p"))
    assert reply == "ok"
    assert sleeps == [5.0, 2.0]


def test_groq_gives_up_after_retries_and_hides_the_key(tmp_path: Path) -> None:
    recorder = Recorder(*(httpx.Response(500, text="boom") for _ in range(3)))
    context = groq_context(tmp_path, recorder, key="secret-key")
    adapter = GroqText(GroqOptions(max_retries=2), context)
    with pytest.raises(UpstreamFailure) as raised:
        adapter.generate(TextRequest(prompt="p"))
    assert "HTTP 500" in raised.value.message
    assert "secret-key" not in raised.value.message
    assert len(recorder.requests) == 3


def test_groq_does_not_retry_client_errors(tmp_path: Path) -> None:
    recorder = Recorder(httpx.Response(401, text="bad key"))
    context = groq_context(tmp_path, recorder)
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


def test_groq_retries_after_a_network_error(tmp_path: Path) -> None:
    sleeps: list[float] = []
    recorder = Recorder(httpx.ConnectError("down"), chat_reply("ok"))
    context = groq_context(tmp_path, recorder, sleeps)
    reply = GroqText(GroqOptions(backoff_seconds=1.0), context).generate(TextRequest(prompt="p"))
    assert reply == "ok"
    assert sleeps == [1.0]


def test_unreadable_retry_after_falls_back_to_backoff(tmp_path: Path) -> None:
    sleeps: list[float] = []
    recorder = Recorder(httpx.Response(429, headers={"retry-after": "soon"}), chat_reply("ok"))
    context = groq_context(tmp_path, recorder, sleeps)
    GroqText(GroqOptions(backoff_seconds=3.0), context).generate(TextRequest(prompt="p"))
    assert sleeps == [3.0]


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(200, text="not json"), "Groq returned invalid JSON"),
        (httpx.Response(200, json=[1]), "Groq returned an unexpected JSON shape"),
        (httpx.Response(200, json={"choices": []}), "Groq response is missing"),
    ],
    ids=["invalid json", "not an object", "no choices"],
)
def test_groq_rejects_malformed_bodies(
    tmp_path: Path, response: httpx.Response, message: str
) -> None:
    context = groq_context(tmp_path, Recorder(response))
    with pytest.raises(UpstreamFailure, match=message):
        GroqText(GroqOptions(), context).generate(TextRequest(prompt="p"))
