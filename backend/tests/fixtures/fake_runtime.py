from __future__ import annotations

import shutil
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from autotube.domain.pipeline import NewArtifact
from autotube.domain.run_parts import Artifact
from autotube.domain.runs import RunEvent
from autotube.domain.schedule_timing import StartCounter, next_run_at, no_starts
from autotube.domain.schedules import Schedule

START = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, start: datetime = START) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> datetime:
        self.current += timedelta(**delta)
        return self.current


class SequentialIds:
    def __init__(self, prefix: str = "id") -> None:
        self.prefix = prefix
        self.count = 0

    def new(self) -> str:
        self.count += 1
        return f"{self.prefix}-{self.count}"


class PureScheduleCalculator:
    def next_run_at(
        self, schedule: Schedule, after: datetime, started_on: StartCounter = no_starts
    ) -> datetime | None:
        return next_run_at(schedule, after, started_on)


class InMemorySecrets:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, name: str) -> str | None:
        return self.values.get(name)

    def set(self, name: str, value: str) -> None:
        self.values[name] = value

    def delete(self, name: str) -> None:
        self.values.pop(name, None)

    def has(self, name: str) -> bool:
        return name in self.values


class InMemoryQuotaLedger:
    def __init__(self) -> None:
        self.units: dict[tuple[str, date], int] = {}

    def used_today(self, credential_id: str, day: date) -> int:
        return self.units.get((credential_id, day), 0)

    def record(self, credential_id: str, units: int, day: date) -> None:
        key = (credential_id, day)
        self.units[key] = self.units.get(key, 0) + units


class RecordingQueue:
    def __init__(self) -> None:
        self.enqueued: list[str] = []
        self.cancelled: list[str] = []

    def enqueue(self, run_id: str) -> None:
        self.enqueued.append(run_id)

    def cancel(self, run_id: str) -> None:
        self.cancelled.append(run_id)


class RecordingEvents:
    def __init__(self) -> None:
        self.published: list[RunEvent] = []

    def publish(self, event: RunEvent) -> None:
        self.published.append(event)

    async def subscribe(self) -> AsyncIterator[RunEvent]:
        for event in list(self.published):
            yield event


class TmpArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.discarded: list[str] = []

    def workspace(self, run_id: str) -> Path:
        path = self.root / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, run_id: str, artifact_id: str, stage_id: str, new: NewArtifact) -> Artifact:
        return Artifact(
            id=artifact_id,
            kind=new.kind,
            stage_id=stage_id,
            language=new.language,
            variant=new.variant,
            filename=new.path.relative_to(self.workspace(run_id)).as_posix(),
            media_type=new.media_type,
            size_bytes=new.path.stat().st_size,
            meta=new.meta,
        )

    def open(self, run_id: str, artifact: Artifact) -> Path:
        return self.workspace(run_id) / artifact.filename

    def discard(self, run_id: str, artifact: Artifact) -> None:
        self.discarded.append(artifact.id)
        self.open(run_id, artifact).unlink(missing_ok=True)

    def delete_run(self, run_id: str) -> None:
        shutil.rmtree(self.root / run_id, ignore_errors=True)
