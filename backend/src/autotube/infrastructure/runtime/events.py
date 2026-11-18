from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from autotube.domain.runs import RunEvent


@dataclass(eq=False)
class Subscriber:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[RunEvent]
    dropped: int = field(default=0)

    def offer(self, event: RunEvent) -> None:
        if self.queue.full():
            self.queue.get_nowait()
            self.dropped += 1
        self.queue.put_nowait(event)


class InProcessRunEvents:
    def __init__(self, queue_size: int) -> None:
        self.queue_size = queue_size
        self.subscribers: set[Subscriber] = set()
        self.lock = threading.Lock()

    def publish(self, event: RunEvent) -> None:
        with self.lock:
            subscribers = list(self.subscribers)
        for subscriber in subscribers:
            self.deliver(subscriber, event)

    def deliver(self, subscriber: Subscriber, event: RunEvent) -> None:
        try:
            subscriber.loop.call_soon_threadsafe(subscriber.offer, event)
        except RuntimeError:
            self.remove(subscriber)

    def remove(self, subscriber: Subscriber) -> None:
        with self.lock:
            self.subscribers.discard(subscriber)

    def subscriber_count(self) -> int:
        with self.lock:
            return len(self.subscribers)

    def register(self) -> Subscriber:
        subscriber = Subscriber(asyncio.get_running_loop(), asyncio.Queue(self.queue_size))
        with self.lock:
            self.subscribers.add(subscriber)
        return subscriber

    async def subscribe(self) -> AsyncIterator[RunEvent]:
        subscriber = self.register()
        try:
            while True:
                yield await subscriber.queue.get()
        finally:
            self.remove(subscriber)
