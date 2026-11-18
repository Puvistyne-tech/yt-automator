from __future__ import annotations

import asyncio

import pytest
from starlette.types import Message, Receive, Scope, Send

from automator.api.internal_errors import InternalErrorMiddleware

HTTP_SCOPE: Scope = {"type": "http", "method": "GET", "path": "/", "headers": []}


async def nothing() -> Message:
    return {"type": "http.request", "body": b""}


def collect(app: InternalErrorMiddleware, scope: Scope) -> list[Message]:
    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    asyncio.run(app(scope, nothing, send))
    return sent


async def fails_after_starting(_scope: Scope, _receive: Receive, send: Send) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    raise RuntimeError("late")


async def fails_at_once(_scope: Scope, _receive: Receive, _send: Send) -> None:
    raise RuntimeError("early")


def test_an_error_before_the_response_becomes_a_500() -> None:
    sent = collect(InternalErrorMiddleware(fails_at_once), HTTP_SCOPE)
    assert sent[0]["status"] == 500


def test_an_error_after_the_response_started_is_reraised() -> None:
    with pytest.raises(RuntimeError, match="late"):
        collect(InternalErrorMiddleware(fails_after_starting), HTTP_SCOPE)


def test_other_scopes_pass_through_untouched() -> None:
    with pytest.raises(RuntimeError, match="early"):
        collect(InternalErrorMiddleware(fails_at_once), {"type": "websocket"})
