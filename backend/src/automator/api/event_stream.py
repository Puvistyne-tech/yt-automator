from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable
from typing import Any

from automator.domain.model_base import JsonObject
from automator.domain.run_enums import RunEventKind
from automator.domain.runs import RunEvent

CONNECTED_LINE = ": connected\n\n"
HEARTBEAT_LINE = ": heartbeat\n\n"
DEFAULT_LOG_LEVEL = "info"


def wire_event(event: RunEvent) -> RunEvent:
    if event.kind is not RunEventKind.LOG:
        return event
    payload: JsonObject = {"level": DEFAULT_LOG_LEVEL, "stage_id": None} | event.payload
    return event.model_copy(update={"payload": payload})


def event_line(event: RunEvent) -> str:
    return f"data: {wire_event(event).model_dump_json()}\n\n"


async def close_source(
    source: AsyncIterator[RunEvent], pending: asyncio.Future[Any] | None
) -> None:
    if pending is not None:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
    closer = getattr(source, "aclose", None)
    if closer is not None:
        await closer()


def next_event(source: AsyncIterator[RunEvent]) -> asyncio.Future[RunEvent]:
    awaitable: Awaitable[RunEvent] = anext(source)
    return asyncio.ensure_future(awaitable)


async def event_stream(
    source: AsyncIterator[RunEvent], heartbeat_seconds: float
) -> AsyncIterator[str]:
    yield CONNECTED_LINE
    pending: asyncio.Future[RunEvent] | None = None
    try:
        while True:
            pending = pending or next_event(source)
            done, _ = await asyncio.wait({pending}, timeout=heartbeat_seconds)
            if not done:
                yield HEARTBEAT_LINE
                continue
            finished, pending = pending, None
            try:
                event = finished.result()
            except StopAsyncIteration:
                return
            yield event_line(event)
    finally:
        await close_source(source, pending)
