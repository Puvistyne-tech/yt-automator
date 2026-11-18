from __future__ import annotations

import threading
from collections.abc import Iterator

import pytest

from automator.infrastructure.runtime.worker_pool import WorkerPoolQueue

TIMEOUT = 5.0


class BlockingExecutor:
    def __init__(self) -> None:
        self.release = threading.Event()
        self.lock = threading.Lock()
        self.started: list[str] = []
        self.running = 0
        self.peak = 0

    def __call__(self, run_id: str) -> None:
        with self.lock:
            self.started.append(run_id)
            self.running += 1
            self.peak = max(self.peak, self.running)
        self.release.wait(TIMEOUT)
        with self.lock:
            self.running -= 1
        if run_id == "boom":
            raise RuntimeError("worker exploded")


@pytest.fixture
def executor() -> BlockingExecutor:
    return BlockingExecutor()


@pytest.fixture
def limit() -> list[int]:
    return [2]


@pytest.fixture
def pool(executor: BlockingExecutor, limit: list[int]) -> Iterator[WorkerPoolQueue]:
    queue = WorkerPoolQueue(lambda: limit[0], poll_seconds=0.01)
    queue.start(executor)
    yield queue
    executor.release.set()
    queue.stop(TIMEOUT)


def wait_until(condition: threading.Condition, predicate: object) -> None:
    with condition:
        assert condition.wait_for(predicate, TIMEOUT)  # type: ignore[arg-type]


def test_pool_honours_the_parallel_limit(pool: WorkerPoolQueue, executor: BlockingExecutor) -> None:
    for run_id in ("a", "b", "c", "d"):
        pool.enqueue(run_id)
    wait_until(pool.condition, lambda: len(pool.active) == 2)
    assert list(pool.pending) == ["c", "d"]
    executor.release.set()
    assert pool.wait_idle(TIMEOUT)
    assert sorted(executor.started) == ["a", "b", "c", "d"]
    assert executor.peak == 2


def test_cancel_removes_a_pending_run(pool: WorkerPoolQueue, executor: BlockingExecutor) -> None:
    for run_id in ("a", "b", "c"):
        pool.enqueue(run_id)
    wait_until(pool.condition, lambda: len(pool.active) == 2)
    pool.cancel("c")
    pool.cancel("unknown")
    executor.release.set()
    assert pool.wait_idle(TIMEOUT)
    assert "c" not in executor.started


def test_duplicate_enqueue_runs_once(
    pool: WorkerPoolQueue, executor: BlockingExecutor, limit: list[int]
) -> None:
    limit[0] = 1
    for run_id in ("a", "b", "b", "a"):
        pool.enqueue(run_id)
    executor.release.set()
    assert pool.wait_idle(TIMEOUT)
    assert executor.started.count("b") == 1


def test_a_crashing_run_does_not_stop_the_pool(
    pool: WorkerPoolQueue, executor: BlockingExecutor
) -> None:
    executor.release.set()
    pool.enqueue("boom")
    pool.enqueue("after")
    assert pool.wait_idle(TIMEOUT)
    assert sorted(executor.started) == ["after", "boom"]


def test_enqueue_before_start_is_buffered(executor: BlockingExecutor) -> None:
    queue = WorkerPoolQueue(lambda: 1, poll_seconds=0.01)
    queue.enqueue("early")
    executor.release.set()
    queue.start(executor)
    assert queue.wait_idle(TIMEOUT)
    queue.stop(TIMEOUT)
    assert executor.started == ["early"]
