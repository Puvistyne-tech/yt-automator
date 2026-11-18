from __future__ import annotations

import threading
from datetime import datetime

from autotube.infrastructure.runtime.scheduler import SchedulerTicker
from tests.fixtures.fake_runtime import FakeClock


def test_the_loop_thread_survives_a_failing_tick() -> None:
    clock = FakeClock()
    seen: list[datetime] = []
    third = threading.Event()

    def tick(now: datetime) -> None:
        seen.append(now)
        if len(seen) == 3:
            third.set()
        if len(seen) in (1, 2):
            raise RuntimeError("tick failed")

    ticker = SchedulerTicker((tick,), clock, interval_seconds=0.01)
    ticker.tick_once()
    ticker.start()
    assert third.wait(5)
    ticker.stop(5)
    assert seen[0] == clock.now()
    assert ticker.thread is not None and not ticker.thread.is_alive()


def test_stop_before_start_is_harmless() -> None:
    ticker = SchedulerTicker((lambda _now: None,), FakeClock(), interval_seconds=0.01)
    ticker.stop(1)
    assert ticker.thread is None and ticker.stopped.is_set()


def test_a_failing_job_does_not_stop_the_next_job_in_the_same_tick() -> None:
    seen: list[str] = []

    def failing(_now: datetime) -> None:
        seen.append("due runs")
        raise RuntimeError("database locked")

    ticker = SchedulerTicker((failing, lambda _now: seen.append("cleanup")), FakeClock(), 3600)
    ticker.tick_once()
    assert seen == ["due runs", "cleanup"]
