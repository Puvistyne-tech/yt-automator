from __future__ import annotations

import json
from pathlib import Path

import httpx

from automator.infrastructure.providers.context import ProviderContext
from tests.unit.infrastructure.providers.fakes import make_context


class Recorder:
    def __init__(self, *responses: httpx.Response | httpx.HTTPError) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        outcome = self.responses.pop(0)
        if isinstance(outcome, httpx.HTTPError):
            raise outcome
        return outcome

    def body(self, index: int = 0) -> dict[str, object]:
        loaded: dict[str, object] = json.loads(self.requests[index].content)
        return loaded


def chat_reply(text: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def groq_context(
    tmp_path: Path, recorder: Recorder, sleeps: list[float] | None = None, key: str = "k"
) -> ProviderContext:
    return make_context(tmp_path, handler=recorder, secrets={"groq_api_key": key}, sleeps=sleeps)
