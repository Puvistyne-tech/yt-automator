from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator

from automator.domain.run_enums import RunEventKind
from automator.domain.runs import RunEvent
from automator.infrastructure.runtime.events import InProcessRunEvents
from tests.fixtures.fake_runtime import START


def event(index: int) -> RunEvent:
    return RunEvent(run_id="r", kind=RunEventKind.LOG, at=START, payload={"i": index})


def publish_three(events: InProcessRunEvents) -> None:
    for index in range(3):
        events.publish(event(index))


async def take(stream: AsyncIterator[RunEvent], count: int) -> list[int]:
    return [int(str((await anext(stream)).payload["i"])) for _ in range(count)]


def test_events_fan_out_to_every_subscriber_from_threads() -> None:
    async def scenario() -> tuple[list[int], list[int], int]:
        events = InProcessRunEvents(queue_size=10)
        streams = [events.subscribe(), events.subscribe()]
        firsts = [asyncio.ensure_future(anext(stream)) for stream in streams]
        while events.subscriber_count() < 2:
            await asyncio.sleep(0)
        publisher = threading.Thread(target=publish_three, args=(events,))
        publisher.start()
        publisher.join()
        heads = [int(str((await first).payload["i"])) for first in firsts]
        rests = [await take(stream, 2) for stream in streams]
        for stream in streams:
            await stream.aclose()  # type: ignore[attr-defined]
        return [heads[0], *rests[0]], [heads[1], *rests[1]], events.subscriber_count()

    first, second, remaining = asyncio.run(scenario())
    assert first == second == [0, 1, 2]
    assert remaining == 0


def test_slow_subscribers_keep_only_the_newest_events() -> None:
    async def scenario() -> tuple[list[int], int]:
        events = InProcessRunEvents(queue_size=2)
        subscriber = events.register()
        for index in range(5):
            events.publish(event(index))
        await asyncio.sleep(0)
        kept = [int(str(subscriber.queue.get_nowait().payload["i"])) for _ in range(2)]
        return kept, subscriber.dropped

    assert asyncio.run(scenario()) == ([3, 4], 3)


def test_subscriber_is_dropped_when_its_loop_is_gone() -> None:
    events = InProcessRunEvents(queue_size=2)

    async def register() -> None:
        events.register()

    asyncio.run(register())
    assert events.subscriber_count() == 1
    events.publish(event(1))
    assert events.subscriber_count() == 0
