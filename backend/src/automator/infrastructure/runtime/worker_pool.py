from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable

logger = logging.getLogger(__name__)

RunExecutor = Callable[[str], object]
ParallelLimit = Callable[[], int]


class WorkerPoolQueue:
    def __init__(self, limit: ParallelLimit, poll_seconds: float) -> None:
        self.limit = limit
        self.poll_seconds = poll_seconds
        self.pending: deque[str] = deque()
        self.active: dict[str, threading.Thread] = {}
        self.condition = threading.Condition()
        self.dispatcher: threading.Thread | None = None
        self.executor: RunExecutor | None = None
        self.stopping = False

    def enqueue(self, run_id: str) -> None:
        with self.condition:
            if run_id not in self.pending and run_id not in self.active:
                self.pending.append(run_id)
            self.condition.notify_all()

    def cancel(self, run_id: str) -> None:
        with self.condition:
            if run_id in self.pending:
                self.pending.remove(run_id)
            self.condition.notify_all()

    def start(self, executor: RunExecutor) -> None:
        with self.condition:
            self.executor = executor
            self.stopping = False
        self.dispatcher = threading.Thread(target=self.dispatch, name="run-dispatcher", daemon=True)
        self.dispatcher.start()

    def stop(self, timeout: float) -> None:
        with self.condition:
            self.stopping = True
            self.condition.notify_all()
            workers = list(self.active.values())
        if self.dispatcher is not None:
            self.dispatcher.join(timeout)
        for worker in workers:
            worker.join(timeout)

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
        with self.condition:
            while not self.stopping:
                while self.pending and len(self.active) < self.capacity():
                    self.launch(self.pending.popleft())
                self.condition.wait(self.poll_seconds)

    def launch(self, run_id: str) -> None:
        worker = threading.Thread(target=self.work, args=(run_id,), name=f"run-{run_id}")
        worker.daemon = True
        self.active[run_id] = worker
        worker.start()
        self.condition.notify_all()

    def work(self, run_id: str) -> None:
        try:
            if self.executor is not None:
                self.executor(run_id)
        except Exception:
            logger.exception("run %s crashed in its worker", run_id)
        finally:
            with self.condition:
                self.active.pop(run_id, None)
                self.condition.notify_all()
