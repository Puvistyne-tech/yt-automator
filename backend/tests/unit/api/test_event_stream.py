from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncGenerator, AsyncIterator

from automator.api.event_stream import CONNECTED_LINE, HEARTBEAT_LINE, event_stream
from automator.domain.run_enums import RunEventKind
from automator.domain.runs import RunEvent
from automator.infrastructure.config import RuntimeConfig
from automator.main import Overrides
from tests.fixtures.fake_runtime import START, RecordingEvents
from tests.unit.api.client import data_payloads, wired

EVENT = RunEvent(run_id="r1", kind=RunEventKind.STATUS, at=START, payload={"status": "running"})


def test_event_route_streams_run_events(config: RuntimeConfig, overrides: Overrides) -> None:
    events = RecordingEvents()
    events.publish(EVENT)
    with (
        wired(config, overrides, events=events) as client,
        client.stream("GET", "/api/events") as response,
    ):
        headers = response.headers
        lines = list(response.iter_lines())
    assert headers["content-type"].startswith("text/event-stream")
    assert (headers["cache-control"], headers["x-accel-buffering"]) == ("no-cache", "no")
    assert lines[0] == ": connected"
    assert data_payloads(lines) == [EVENT.model_dump(mode="json")]


async def silent_then_event() -> AsyncIterator[RunEvent]:
    await asyncio.sleep(0.05)
    yield EVENT
    await asyncio.sleep(10)
    yield EVENT


def test_stream_sends_heartbeats_and_closes_its_source() -> None:
    source = silent_then_event()
    assert isinstance(source, AsyncGenerator)

    async def scenario() -> list[str]:
        stream = event_stream(source, heartbeat_seconds=0.01)
        chunks: list[str] = []
        while not chunks or not chunks[-1].startswith("data: "):
            chunks.append(await anext(stream))
        await stream.aclose()  # type: ignore[attr-defined]
        return chunks

    chunks = asyncio.run(scenario())
    assert chunks[0] == CONNECTED_LINE
    assert HEARTBEAT_LINE in chunks
    assert chunks[-1] == f"data: {EVENT.model_dump_json()}\n\n"
    assert inspect.getasyncgenstate(source) == inspect.AGEN_CLOSED


async def forever_silent() -> AsyncIterator[RunEvent]:
    await asyncio.sleep(10)
    yield EVENT


def test_disconnect_while_waiting_cancels_the_pending_read() -> None:
    source = forever_silent()
    assert isinstance(source, AsyncGenerator)

    async def scenario() -> tuple[list[str], int]:
        stream = event_stream(source, heartbeat_seconds=0.01)
        chunks = [await anext(stream), await anext(stream)]
        await stream.aclose()  # type: ignore[attr-defined]
        await asyncio.sleep(0)
        return chunks, len(asyncio.all_tasks())

    chunks, tasks = asyncio.run(scenario())
    assert chunks == [CONNECTED_LINE, HEARTBEAT_LINE]
    assert tasks == 1
    assert inspect.getasyncgenstate(source) == inspect.AGEN_CLOSED


class PlainSource:
    def __init__(self) -> None:
        self.remaining = [EVENT]

    def __aiter__(self) -> PlainSource:
        return self

    async def __anext__(self) -> RunEvent:
        if not self.remaining:
            raise StopAsyncIteration
        return self.remaining.pop()


def test_a_source_without_aclose_ends_cleanly() -> None:
    async def scenario() -> list[str]:
        return [chunk async for chunk in event_stream(PlainSource(), heartbeat_seconds=1)]

    assert asyncio.run(scenario()) == [CONNECTED_LINE, f"data: {EVENT.model_dump_json()}\n\n"]
