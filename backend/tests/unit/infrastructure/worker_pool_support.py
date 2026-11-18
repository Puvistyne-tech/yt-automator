from __future__ import annotations

import threading

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


def wait_until(condition: threading.Condition, predicate: object) -> None:
    with condition:
        assert condition.wait_for(predicate, TIMEOUT)  # type: ignore[arg-type]
