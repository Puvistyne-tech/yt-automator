from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable

logger = logging.getLogger(__name__)

RunExecutor = Callable[[str], object]
ParallelLimit = Callable[[], int]


def remaining(deadline: float) -> float:
    return max(deadline - time.monotonic(), 0.0)


class WorkerPoolQueue:
    def __init__(self, limit: ParallelLimit, poll_seconds: float) -> None:
        self.limit = limit
        self.poll_seconds = poll_seconds
        self.pending: deque[str] = deque()
        self.active: dict[str, threading.Thread] = {}
        self.requeue: set[str] = set()
        self.condition = threading.Condition()
        self.dispatcher: threading.Thread | None = None
        self.executor: RunExecutor | None = None
        self.stopping = False

    def enqueue(self, run_id: str) -> None:
        with self.condition:
            if run_id in self.active:
                self.requeue.add(run_id)
            elif run_id not in self.pending:
                self.pending.append(run_id)
            self.condition.notify_all()

    def cancel(self, run_id: str) -> None:
        with self.condition:
            if run_id in self.pending:
                self.pending.remove(run_id)
            self.requeue.discard(run_id)
            self.condition.notify_all()

    def start(self, executor: RunExecutor) -> None:
        with self.condition:
            self.executor = executor
            self.stopping = False
        self.dispatcher = threading.Thread(target=self.dispatch, name="run-dispatcher", daemon=True)
        self.dispatcher.start()

    def stop(self, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        with self.condition:
            self.stopping = True
            self.condition.notify_all()
            threads = [self.dispatcher, *self.active.values()]
        alive = [thread for thread in threads if thread is not None]
        for thread in alive:
            thread.join(remaining(deadline))
        return not any(thread.is_alive() for thread in alive)

    def wait_idle(self, timeout: float) -> bool:
        with self.condition:
            return self.condition.wait_for(lambda: not self.pending and not self.active, timeout)

    def capacity(self) -> int:
        try:
            return max(self.limit(), 1)
        except Exception:
            logger.exception("could not read the parallel run limit")
            return 1

    def dispatch(self) -> None:
        while True:
            limit = self.capacity()
            with self.condition:
                if self.stopping:
                    return
                while self.pending and len(self.active) < limit:
                    self.launch(self.pending.popleft())
                self.condition.wait(self.poll_seconds)

    def launch(self, run_id: str) -> None:
        worker = threading.Thread(target=self.work, args=(run_id,), name=f"run-{run_id}")
        worker.daemon = True
        self.active[run_id] = worker
        worker.start()
        self.condition.notify_all()

    def finish(self, run_id: str) -> None:
        with self.condition:
            self.active.pop(run_id, None)
            if run_id in self.requeue:
                self.requeue.discard(run_id)
                self.pending.append(run_id)
            self.condition.notify_all()

    def work(self, run_id: str) -> None:
        try:
            if self.executor is not None:
                self.executor(run_id)
        except Exception:
            logger.exception("run %s crashed in its worker", run_id)
        finally:
            self.finish(run_id)
