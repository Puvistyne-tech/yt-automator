from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from datetime import datetime

from automator.domain.ports import Clock

logger = logging.getLogger(__name__)

Tick = Callable[[datetime], object]


class SchedulerTicker:
    def __init__(self, ticks: Sequence[Tick], clock: Clock, interval_seconds: float) -> None:
        self.ticks = tuple(ticks)
        self.clock = clock
        self.interval_seconds = interval_seconds
        self.stopped = threading.Event()
        self.thread: threading.Thread | None = None

    def tick_once(self) -> None:
        now = self.clock.now()
        for tick in self.ticks:
            try:
                tick(now)
            except Exception:
                logger.exception("scheduler tick failed")

    def loop(self) -> None:
        while not self.stopped.wait(self.interval_seconds):
            self.tick_once()

    def start(self) -> None:
        self.stopped.clear()
        self.thread = threading.Thread(target=self.loop, name="scheduler", daemon=True)
        self.thread.start()

    def stop(self, timeout: float) -> None:
        self.stopped.set()
        if self.thread is not None:
            self.thread.join(timeout)
