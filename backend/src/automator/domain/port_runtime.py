from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from automator.domain.diagnostics import SystemFacts
from automator.domain.pipeline import NewArtifact
from automator.domain.run_parts import Artifact
from automator.domain.runs import RunEvent
from automator.domain.schedule_timing import StartCounter
from automator.domain.schedules import Schedule
from automator.domain.storage import DiskSpace, FileUsage


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new(self) -> str: ...


class SecretStore(Protocol):
    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...

    def has(self, name: str) -> bool: ...


class QuotaLedger(Protocol):
    def used_today(self, credential_id: str, day: date) -> int: ...

    def record(self, credential_id: str, units: int, day: date) -> None: ...


class ScheduleCalculator(Protocol):
    def next_run_at(
        self, schedule: Schedule, after: datetime, started_on: StartCounter
    ) -> datetime | None: ...


class ArtifactStore(Protocol):
    def workspace(self, run_id: str) -> Path: ...

    def save(self, run_id: str, artifact_id: str, stage_id: str, new: NewArtifact) -> Artifact: ...

    def open(self, run_id: str, artifact: Artifact) -> Path: ...

    def discard(self, run_id: str, artifact: Artifact) -> None: ...

    def delete_run(self, run_id: str) -> None: ...


class RunFileStore(Protocol):
    def run_ids(self) -> frozenset[str]: ...

    def usage(self, run_id: str, final_ids: frozenset[str]) -> FileUsage: ...

    def remove_intermediate(self, run_id: str, final_ids: frozenset[str]) -> int: ...

    def delete_run(self, run_id: str) -> int: ...

    def disk(self) -> DiskSpace: ...


class RunQueue(Protocol):
    def enqueue(self, run_id: str) -> None: ...

    def cancel(self, run_id: str) -> None: ...


class RunEvents(Protocol):
    def publish(self, event: RunEvent) -> None: ...

    def subscribe(self) -> AsyncIterator[RunEvent]: ...


class SystemInspector(Protocol):
    def facts(self) -> SystemFacts: ...
