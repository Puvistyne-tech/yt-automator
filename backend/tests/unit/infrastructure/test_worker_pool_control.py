from __future__ import annotations

import threading
import time

import pytest

from autotube.infrastructure.runtime.worker_pool import ParallelLimit, WorkerPoolQueue
from tests.unit.infrastructure.worker_pool_support import (
    TIMEOUT,
    BlockingExecutor,
    wait_until,
)


def test_enqueue_while_active_runs_again_after_it_finishes(
    pool: WorkerPoolQueue, executor: BlockingExecutor
) -> None:
    pool.enqueue("a")
    wait_until(pool.condition, lambda: "a" in pool.active)
    pool.enqueue("a")
    pool.enqueue("a")
    assert pool.requeue == {"a"} and list(pool.pending) == []
    executor.release.set()
    assert pool.wait_idle(TIMEOUT)
    assert executor.started == ["a", "a"]


def test_cancelling_an_active_run_keeps_it_working_and_drops_its_requeue(
    pool: WorkerPoolQueue, executor: BlockingExecutor
) -> None:
    pool.enqueue("a")
    wait_until(pool.condition, lambda: "a" in pool.active)
    pool.enqueue("a")
    pool.cancel("a")
    assert "a" in pool.active and pool.requeue == set()
    executor.release.set()
    assert pool.wait_idle(TIMEOUT)
    assert executor.started == ["a"]


def failing_limit() -> int:
    raise RuntimeError("settings unreadable")


@pytest.mark.parametrize("read_limit", [lambda: 0, failing_limit])
def test_a_zero_or_unreadable_limit_runs_one_at_a_time(
    executor: BlockingExecutor, read_limit: ParallelLimit
) -> None:
    queue = WorkerPoolQueue(read_limit, poll_seconds=0.01)
    queue.start(executor)
    for run_id in ("a", "b", "c"):
        queue.enqueue(run_id)
    executor.release.set()
    assert queue.wait_idle(TIMEOUT)
    assert queue.stop(TIMEOUT)
    assert executor.peak == 1 and sorted(executor.started) == ["a", "b", "c"]


def test_raising_the_limit_launches_pending_runs(
    pool: WorkerPoolQueue, executor: BlockingExecutor, limit: list[int]
) -> None:
    limit[0] = 1
    for run_id in ("a", "b", "c"):
        pool.enqueue(run_id)
    wait_until(pool.condition, lambda: len(pool.active) == 1)
    limit[0] = 3
    wait_until(pool.condition, lambda: len(pool.active) == 3)
    executor.release.set()
    assert pool.wait_idle(TIMEOUT)


def test_a_slow_limit_read_does_not_block_enqueue(executor: BlockingExecutor) -> None:
    reading, gate = threading.Event(), threading.Event()

    def slow_limit() -> int:
        reading.set()
        gate.wait(TIMEOUT * 4)
        return 1

    queue = WorkerPoolQueue(slow_limit, poll_seconds=0.01)
    queue.start(executor)
    assert reading.wait(TIMEOUT)
    done = threading.Event()

    def enqueue_and_cancel() -> None:
        queue.enqueue("a")
        queue.cancel("a")
        done.set()

    threading.Thread(target=enqueue_and_cancel, daemon=True).start()
    assert done.wait(TIMEOUT) and not gate.is_set()
    gate.set()
    executor.release.set()
    assert queue.stop(TIMEOUT)


class StuckThread:
    def __init__(self, clock: list[float]) -> None:
        self.clock = clock
        self.timeouts: list[float] = []

    def join(self, timeout: float) -> None:
        self.timeouts.append(timeout)
        self.clock[0] += timeout

    def is_alive(self) -> bool:
        return True


def test_stop_shares_one_deadline_across_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    queue = WorkerPoolQueue(lambda: 3, poll_seconds=0.01)
    threads = [StuckThread(clock) for _ in range(3)]
    queue.active = {str(index): thread for index, thread in enumerate(threads)}  # type: ignore[misc]
    assert queue.stop(0.5) is False
    assert [thread.timeouts for thread in threads] == [[0.5], [0.0], [0.0]]


def test_stop_reports_success_once_workers_finish(
    pool: WorkerPoolQueue, executor: BlockingExecutor, limit: list[int]
) -> None:
    limit[0] = 3
    for run_id in ("a", "b", "c"):
        pool.enqueue(run_id)
    wait_until(pool.condition, lambda: len(pool.active) == 3)
    executor.release.set()
    assert pool.stop(TIMEOUT) is True
