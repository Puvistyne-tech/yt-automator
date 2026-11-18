from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from automator.domain.youtube import ChannelAuth, OAuthClient

CLIENT = OAuthClient(client_id="cid", client_secret="csecret")
VALID_TOKEN = {"token": "at", "refresh_token": "rt", "expiry": "2999-01-01T00:00:00Z"}
EXPIRED_TOKEN = VALID_TOKEN | {"expiry": "2000-01-01T00:00:00Z"}


def auth(token: dict[str, str] | None = None) -> ChannelAuth:
    return ChannelAuth(client=CLIENT, token=json.dumps(token or VALID_TOKEN))


def media(path: str, **options: Any) -> dict[str, Any]:
    return {"path": path} | options


@dataclass
class FakeRequest:
    response: Any
    chunks: int = 1

    def execute(self) -> Any:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def next_chunk(self) -> tuple[Any, Any]:
        self.chunks -= 1
        if self.chunks > 0:
            return ("progress", None)
        return (None, self.execute())


@dataclass
class FakeService:
    responses: dict[tuple[str, str], list[Any]] = field(default_factory=dict)
    calls: list[tuple[str, str, dict[str, Any]]] = field(default_factory=list)
    chunks: int = 1

    def respond(self, resource: str, method: str, *responses: Any) -> None:
        self.responses[(resource, method)] = list(responses)

    def request(self, resource: str, method: str, kwargs: dict[str, Any]) -> FakeRequest:
        self.calls.append((resource, method, kwargs))
        queued = self.responses.get((resource, method), [{}])
        response = queued.pop(0) if len(queued) > 1 else queued[0]
        return FakeRequest(response, self.chunks)

    def __getattr__(self, resource: str) -> Any:
        return lambda: FakeResource(self, resource)


@dataclass
class FakeResource:
    service: FakeService
    name: str

    def __getattr__(self, method: str) -> Any:
        return lambda **kwargs: self.service.request(self.name, method, kwargs)
