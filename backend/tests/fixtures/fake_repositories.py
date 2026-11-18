from __future__ import annotations

import builtins
import threading
from collections.abc import Sequence
from typing import Protocol

from automator.domain.automations import Automation
from automator.domain.channels import Channel
from automator.domain.credentials import Credential
from automator.domain.ports import RunChange
from automator.domain.providers import ProviderConfig
from automator.domain.runs import Run, RunQuery
from automator.domain.settings import AppSettings


class HasId(Protocol):
    @property
    def id(self) -> str: ...


class InMemoryStore[T: HasId]:
    def __init__(self) -> None:
        self.items: dict[str, T] = {}

    def get(self, item_id: str) -> T | None:
        return self.items.get(item_id)

    def list(self) -> builtins.list[T]:
        return builtins.list(self.items.values())

    def save(self, item: T) -> None:
        self.items[item.id] = item

    def delete(self, item_id: str) -> None:
        self.items.pop(item_id, None)


class InMemoryCredentials(InMemoryStore[Credential]):
    pass


class InMemoryAutomations(InMemoryStore[Automation]):
    pass


class InMemoryChannels(InMemoryStore[Channel]):
    def find_by_youtube_id(self, youtube_channel_id: str) -> Channel | None:
        return next(
            (c for c in self.items.values() if c.youtube_channel_id == youtube_channel_id), None
        )


def run_matches(run: Run, query: RunQuery) -> bool:
    return (
        (query.automation_id is None or run.automation_id == query.automation_id)
        and (query.status is None or run.status is query.status)
        and (query.trigger is None or run.trigger is query.trigger)
        and (query.created_after is None or run.created_at >= query.created_after)
    )


class InMemoryRuns:
    def __init__(self) -> None:
        self.items: dict[str, Run] = {}
        self.saves = 0
        self.lock = threading.RLock()

    def get(self, run_id: str) -> Run | None:
        return self.items.get(run_id)

    def list(self, query: RunQuery) -> list[Run]:
        found = [run for run in self.items.values() if run_matches(run, query)]
        found.sort(key=lambda run: (run.created_at, run.id), reverse=True)
        return found[: query.limit] if query.limit is not None else found

    def save(self, run: Run) -> None:
        self.saves += 1
        self.items[run.id] = run

    def update(self, run_id: str, change: RunChange) -> Run | None:
        with self.lock:
            stored = self.items.get(run_id)
            changed = change(stored) if stored is not None else None
            if changed is not None:
                self.save(changed)
            return changed

    def delete(self, run_id: str) -> None:
        self.items.pop(run_id, None)


class InMemoryProviderConfigs:
    def __init__(self) -> None:
        self.configs: list[ProviderConfig] = []

    def list(self) -> list[ProviderConfig]:
        return list(self.configs)

    def save_all(self, configs: Sequence[ProviderConfig]) -> None:
        self.configs = list(configs)


class InMemoryAppSettings:
    def __init__(self, data_dir: str = "/tmp/automator") -> None:
        self.settings = AppSettings(data_dir=data_dir)

    def get(self) -> AppSettings:
        return self.settings

    def save(self, settings: AppSettings) -> None:
        self.settings = settings
