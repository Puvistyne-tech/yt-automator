from __future__ import annotations

import builtins
import threading
from collections.abc import Sequence
from typing import Protocol

from autotube.domain.automations import Automation
from autotube.domain.channels import Channel
from autotube.domain.credentials import Credential
from autotube.domain.pipeline_templates import PipelineTemplate
from autotube.domain.ports import RunChange, RunCheck
from autotube.domain.providers import ProviderConfig
from autotube.domain.runs import Run, RunQuery
from autotube.domain.settings import AppSettings, AppSettingsInput
from autotube.domain.settings_overrides import (
    Overrides,
    effective_settings,
    storable_settings,
)
from autotube.domain.template_rules import ensure_new_id, ensure_type_id_owned


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


class InMemoryTemplates(InMemoryStore[PipelineTemplate]):
    def __init__(self) -> None:
        super().__init__()
        self.undecodable: dict[str, str] = {}

    def type_id_of(self, template_id: str) -> str | None:
        stored = self.items.get(template_id)
        return stored.type_id if stored is not None else self.undecodable.get(template_id)

    def delete(self, item_id: str) -> None:
        super().delete(item_id)
        self.undecodable.pop(item_id, None)

    def find_by_type_id(self, type_id: str) -> PipelineTemplate | None:
        return next((t for t in self.items.values() if t.type_id == type_id), None)

    def list(self) -> builtins.list[PipelineTemplate]:
        return sorted(self.items.values(), key=lambda template: template.created_at)

    def holder_id(self, type_id: str) -> str | None:
        holder = self.find_by_type_id(type_id)
        return holder.id if holder is not None else None

    def add(self, template: PipelineTemplate) -> None:
        ensure_new_id(template.id, template.id in self.items)
        self.update(template)

    def update(self, template: PipelineTemplate) -> None:
        ensure_type_id_owned(template, self.holder_id(template.type_id))
        self.save(template)


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

    def delete_if(self, run_id: str, check: RunCheck) -> Run | None:
        with self.lock:
            stored = self.items.get(run_id)
            if stored is None or not check(stored):
                return None
            return self.items.pop(run_id)


class InMemoryProviderConfigs:
    def __init__(self) -> None:
        self.configs: list[ProviderConfig] = []

    def list(self) -> list[ProviderConfig]:
        return list(self.configs)

    def save_all(self, configs: Sequence[ProviderConfig]) -> None:
        self.configs = list(configs)


class InMemoryAppSettings:
    def __init__(self, data_dir: str = "/tmp/autotube", overrides: Overrides = ()) -> None:
        self.data_dir = data_dir
        self.overrides = tuple(overrides)
        self.stored = AppSettingsInput()

    def get(self) -> AppSettings:
        return effective_settings(self.stored, self.overrides, self.data_dir)

    def save(self, settings: AppSettings) -> None:
        self.stored = storable_settings(settings.input(), self.stored, list(settings.locked))
